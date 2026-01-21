import sqlite3
import time
import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime
from contextlib import contextmanager

# Setup Logging
logger = logging.getLogger("Database")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emails.db")

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
    """Initialize the database with the emails table."""
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

def get_recent_emails(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db_cursor() as c:
        c.execute("SELECT * FROM emails ORDER BY ingested_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [dict(row) for row in rows]
