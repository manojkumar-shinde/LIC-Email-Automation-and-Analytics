import sqlite3
import time
import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime
from contextlib import contextmanager
from cryptography.fernet import Fernet
import base64
import hashlib

# Setup Logging
logger = logging.getLogger("Database")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emails.db")

# Encryption key for storing Gmail credentials
# In production, load from environment variable: os.getenv('ENCRYPTION_KEY')
# This is a default key - should be changed in production!
def get_encryption_key():
    """Get or generate encryption key for credentials"""
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".encryption_key")
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Generate new key
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        logger.info("Generated new encryption key for credentials")
        return key

# Initialize encryption cipher
_encryption_key = get_encryption_key()
_cipher_suite = Fernet(_encryption_key)

def encrypt_credential(credential: str) -> str:
    """Encrypt a credential string"""
    try:
        encrypted = _cipher_suite.encrypt(credential.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise

def decrypt_credential(encrypted_credential: str) -> str:
    """Decrypt a credential string"""
    try:
        decoded = base64.b64decode(encrypted_credential.encode())
        decrypted = _cipher_suite.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise

@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager for database connections.
    Handles connection creation, commit/rollback, and closing.
    Enables WAL mode for concurrency.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;") # Faster, still safe enough for most usage

    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        if commit:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database with the emails and gmail_config tables."""
    logger.info(f"Initializing database at {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_db_cursor(commit=True) as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                sender TEXT,
                subject TEXT,
                body_original TEXT,
                body_redacted TEXT,
                analysis TEXT, -- JSON String
                suggested_action TEXT,
                status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
                received_at DATETIME,
                ingested_at DATETIME,
                processed_at DATETIME,
                processing_started_at DATETIME
            )
        ''')
        # Create indexes for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_status ON emails(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ingested_at ON emails(ingested_at)")
        
        # Schema Migration: Ensure processing_started_at exists
        try:
            c.execute("SELECT processing_started_at FROM emails LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Migrating database: Adding processing_started_at column")
            c.execute("ALTER TABLE emails ADD COLUMN processing_started_at DATETIME")
        
        # Create Gmail Config Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS gmail_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_email TEXT UNIQUE NOT NULL,
                auth_method TEXT NOT NULL, -- 'oauth', 'service_account', or 'token'
                credentials_encrypted TEXT NOT NULL, -- Encrypted API key/token/JSON
                credentials_hash TEXT NOT NULL, -- Hash for verification
                sync_enabled BOOLEAN DEFAULT 1,
                last_sync_time DATETIME,
                last_sync_status TEXT, -- 'success', 'failed', 'pending'
                last_sync_error TEXT,
                total_synced INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create indexes for gmail_config
        c.execute("CREATE INDEX IF NOT EXISTS idx_gmail_email ON gmail_config(gmail_email)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sync_enabled ON gmail_config(sync_enabled)")
        
        logger.info("Database initialized successfully")

def save_email(google_id: str, sender: str, subject: str, body: str, received_at: datetime) -> bool:
    """Save a new email to the database. Returns True if saved, False if duplicate."""
    try:
        with get_db_cursor(commit=True) as c:
            c.execute('''
                INSERT INTO emails (google_id, sender, subject, body_original, received_at, ingested_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ''', (google_id, sender, subject, body, received_at, datetime.now()))
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Duplicate email skipped: {google_id}")
        return False
    except Exception:
        # Generic error already logged by context manager
        return False

def bulk_save_emails(emails: List[Dict[str, Any]]) -> int:
    """
    Save multiple emails to the database.
    Expects list of dicts with: google_id, sender, subject, body, received_at
    Returns number of emails successfully saved.
    """
    data = []
    now = datetime.now()
    for e in emails:
        data.append((
            e['google_id'],
            e['sender'],
            e['subject'],
            e['body'],
            e['received_at'],
            now
        ))
        
    try:
        with get_db_cursor(commit=True) as c:
            # INSERT OR IGNORE avoids aborting the whole transaction on duplicates
            c.executemany('''
                INSERT OR IGNORE INTO emails (google_id, sender, subject, body_original, received_at, ingested_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ''', data)
            return c.rowcount
    except Exception:
        return 0

def get_pending_email() -> Optional[Dict[str, Any]]:
    """Legacy: Get oldest pending email (Read-only)."""
    # Kept for backward compatibility, but 'claim_next_pending_email' is preferred for workers.
    with get_db_cursor() as c:
        c.execute("SELECT * FROM emails WHERE status = 'PENDING' ORDER BY ingested_at ASC LIMIT 1")
        row = c.fetchone()
        return dict(row) if row else None

def claim_next_pending_email() -> Optional[Dict[str, Any]]:
    """
    Atomically claim the oldest pending email for processing.
    Sets status to 'PROCESSING' to prevent race conditions.
    """
    # SQLite Tweak: Use immediate transaction to lock for writing
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;") 
    
    try:
        conn.execute("BEGIN IMMEDIATE") # Lock DB for writing
        c = conn.cursor()
        
        # Find oldest pending
        c.execute("SELECT id FROM emails WHERE status = 'PENDING' ORDER BY ingested_at ASC LIMIT 1")
        row = c.fetchone()
        
        if row:
            email_id = row['id']
            now = datetime.now()
            # Mark as processing
            c.execute("UPDATE emails SET status = 'PROCESSING', processing_started_at = ? WHERE id = ?", (now, email_id))
            
            # Fetch full data to return
            c.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            email_data = c.fetchone()
            
            conn.commit()
            return dict(email_data)
        else:
            conn.commit() # Nothing to do
            return None
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error claiming email: {e}")
        return None
    finally:
        conn.close()

def update_email_analysis(email_id: int, redacted_body: str, analysis: Dict[str, Any], suggested_action: str, status: str = 'COMPLETED'):
    with get_db_cursor(commit=True) as c:
        c.execute('''
            UPDATE emails 
            SET body_redacted = ?, analysis = ?, suggested_action = ?, status = ?, processed_at = ?
            WHERE id = ?
        ''', (redacted_body, json.dumps(analysis), suggested_action, status, datetime.now(), email_id))

def get_stats() -> Dict[str, Any]:
    with get_db_cursor() as c:
        # Counts
        c.execute("SELECT status, COUNT(*) FROM emails GROUP BY status")
        counts = dict(c.fetchall())
        
        # Avg Latency (Processed Time - Ingested Time)
        c.execute('''
            SELECT AVG((julianday(processed_at) - julianday(ingested_at)) * 86400.0) 
            FROM emails 
            WHERE status = 'COMPLETED'
        ''')
        row = c.fetchone()
        avg_latency = row[0] if row and row[0] else 0.0
        
    return {
        "pending": counts.get('PENDING', 0),
        "processing": counts.get('PROCESSING', 0),
        "completed": counts.get('COMPLETED', 0),
        "failed": counts.get('FAILED', 0),
        "avg_latency": round(avg_latency, 2)
    }

def get_recent_emails(page: int = 1, limit: int = 20) -> Dict[str, Any]:
    offset = (page - 1) * limit
    with get_db_cursor() as c:
        # Get total count
        c.execute("SELECT COUNT(*) FROM emails")
        row = c.fetchone()
        total = row[0] if row else 0
        
        # Get paged items
        c.execute("SELECT * FROM emails ORDER BY ingested_at ASC LIMIT ? OFFSET ?", (limit, offset))
        rows = c.fetchall()
        
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "size": limit
        }


# ============================================================================
# GMAIL CONFIG FUNCTIONS
# ============================================================================

def save_gmail_config(gmail_email: str, auth_method: str, credentials: str) -> bool:
    """
    Save or update Gmail configuration with encrypted credentials.
    
    Args:
        gmail_email: Gmail account email address
        auth_method: Authentication method ('oauth', 'service_account', 'token')
        credentials: API key, token, or JSON credentials string
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        encrypted_creds = encrypt_credential(credentials)
        # Hash credentials for verification (without storing plaintext)
        creds_hash = hashlib.sha256(credentials.encode()).hexdigest()
        
        with get_db_cursor(commit=True) as c:
            # Try to update existing config first
            c.execute('''
                UPDATE gmail_config 
                SET auth_method = ?, credentials_encrypted = ?, credentials_hash = ?, updated_at = ?
                WHERE gmail_email = ?
            ''', (auth_method, encrypted_creds, creds_hash, datetime.now(), gmail_email))
            
            # If no rows updated, insert new config
            if c.rowcount == 0:
                c.execute('''
                    INSERT INTO gmail_config (gmail_email, auth_method, credentials_encrypted, credentials_hash, last_sync_status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (gmail_email, auth_method, encrypted_creds, creds_hash))
        
        logger.info(f"Gmail config saved for {gmail_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving Gmail config: {e}")
        return False


def get_gmail_config(gmail_email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve Gmail configuration (with decrypted credentials).
    
    Args:
        gmail_email: Gmail account email address
        
    Returns:
        Dictionary with config or None if not found
    """
    try:
        with get_db_cursor() as c:
            c.execute("SELECT * FROM gmail_config WHERE gmail_email = ?", (gmail_email,))
            row = c.fetchone()
            
            if row:
                config = dict(row)
                # Decrypt credentials
                config['credentials'] = decrypt_credential(config['credentials_encrypted'])
                # Remove encrypted version from response (optional)
                config.pop('credentials_encrypted', None)
                config.pop('credentials_hash', None)
                return config
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving Gmail config: {e}")
        return None


def get_all_gmail_configs(enabled_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieve all Gmail configurations.
    
    Args:
        enabled_only: Only return enabled configs
        
    Returns:
        List of configuration dictionaries
    """
    try:
        with get_db_cursor() as c:
            if enabled_only:
                c.execute("SELECT * FROM gmail_config WHERE sync_enabled = 1")
            else:
                c.execute("SELECT * FROM gmail_config")
            
            rows = c.fetchall()
            configs = []
            
            for row in rows:
                config = dict(row)
                # Decrypt credentials
                try:
                    config['credentials'] = decrypt_credential(config['credentials_encrypted'])
                except Exception as e:
                    logger.warning(f"Could not decrypt credentials for {config['gmail_email']}: {e}")
                    config['credentials'] = None
                
                # Remove sensitive data from response
                config.pop('credentials_encrypted', None)
                config.pop('credentials_hash', None)
                configs.append(config)
            
            return configs
            
    except Exception as e:
        logger.error(f"Error retrieving Gmail configs: {e}")
        return []


def update_gmail_sync_status(gmail_email: str, status: str, error_msg: str = None) -> bool:
    """
    Update Gmail sync status and error information.
    
    Args:
        gmail_email: Gmail account email address
        status: Sync status ('success', 'failed', 'pending', 'syncing')
        error_msg: Error message if sync failed
        
    Returns:
        True if updated successfully
    """
    try:
        with get_db_cursor(commit=True) as c:
            c.execute('''
                UPDATE gmail_config 
                SET last_sync_time = ?, last_sync_status = ?, last_sync_error = ?, updated_at = ?
                WHERE gmail_email = ?
            ''', (datetime.now(), status, error_msg, datetime.now(), gmail_email))
        
        logger.info(f"Gmail sync status updated for {gmail_email}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating Gmail sync status: {e}")
        return False


def increment_gmail_sync_count(gmail_email: str, count: int = 1) -> bool:
    """
    Increment the number of emails synced from Gmail account.
    
    Args:
        gmail_email: Gmail account email address
        count: Number to increment by
        
    Returns:
        True if updated successfully
    """
    try:
        with get_db_cursor(commit=True) as c:
            c.execute('''
                UPDATE gmail_config 
                SET total_synced = total_synced + ?, updated_at = ?
                WHERE gmail_email = ?
            ''', (count, datetime.now(), gmail_email))
        
        return True
        
    except Exception as e:
        logger.error(f"Error incrementing Gmail sync count: {e}")
        return False


def toggle_gmail_sync(gmail_email: str, enabled: bool) -> bool:
    """
    Enable or disable Gmail sync for an account.
    
    Args:
        gmail_email: Gmail account email address
        enabled: True to enable, False to disable
        
    Returns:
        True if updated successfully
    """
    try:
        with get_db_cursor(commit=True) as c:
            c.execute('''
                UPDATE gmail_config 
                SET sync_enabled = ?, updated_at = ?
                WHERE gmail_email = ?
            ''', (1 if enabled else 0, datetime.now(), gmail_email))
        
        logger.info(f"Gmail sync toggled for {gmail_email}: {enabled}")
        return True
        
    except Exception as e:
        logger.error(f"Error toggling Gmail sync: {e}")
        return False


def delete_gmail_config(gmail_email: str) -> bool:
    """
    Delete Gmail configuration.
    
    Args:
        gmail_email: Gmail account email address
        
    Returns:
        True if deleted successfully
    """
    try:
        with get_db_cursor(commit=True) as c:
            c.execute("DELETE FROM gmail_config WHERE gmail_email = ?", (gmail_email,))
        
        logger.info(f"Gmail config deleted for {gmail_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting Gmail config: {e}")
        return False


def get_gmail_config_stats() -> Dict[str, Any]:
    """
    Get statistics about Gmail configurations.
    
    Returns:
        Dictionary with stats
    """
    try:
        with get_db_cursor() as c:
            # Count total configs
            c.execute("SELECT COUNT(*) FROM gmail_config")
            total = c.fetchone()[0]
            
            # Count enabled configs
            c.execute("SELECT COUNT(*) FROM gmail_config WHERE sync_enabled = 1")
            enabled = c.fetchone()[0]
            
            # Count successful syncs
            c.execute("SELECT COUNT(*) FROM gmail_config WHERE last_sync_status = 'success'")
            successful = c.fetchone()[0]
            
            # Count failed syncs
            c.execute("SELECT COUNT(*) FROM gmail_config WHERE last_sync_status = 'failed'")
            failed = c.fetchone()[0]
            
            # Total emails synced
            c.execute("SELECT SUM(total_synced) FROM gmail_config")
            row = c.fetchone()
            total_synced = row[0] if row and row[0] else 0
        
        return {
            "total_accounts": total,
            "enabled_accounts": enabled,
            "successful_syncs": successful,
            "failed_syncs": failed,
            "total_emails_synced": total_synced
        }
        
    except Exception as e:
        logger.error(f"Error getting Gmail stats: {e}")
        return {}
