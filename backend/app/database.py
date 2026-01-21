import sqlite3
import time
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emails.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the emails table."""
    conn = get_db_connection()
    c = conn.cursor()
    # Dropping table for "Start from Scratch" requirement to ensuring fresh schema
    # c.execute("DROP TABLE IF EXISTS emails")
    
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
            processed_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def save_email(google_id: str, sender: str, subject: str, body: str, received_at: datetime) -> bool:
    """Save a new email to the database. Returns True if saved, False if duplicate."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO emails (google_id, sender, subject, body_original, received_at, ingested_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        ''', (google_id, sender, subject, body, received_at, datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def bulk_save_emails(emails: List[Dict[str, Any]]) -> int:
    """
    Save multiple emails to the database.
    Expects list of dicts with: google_id, sender, subject, body, received_at
    Returns number of emails successfully saved.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Prepare data tuples
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
        # INSERT OR IGNORE avoids aborting the whole transaction on duplicates
        c.executemany('''
            INSERT OR IGNORE INTO emails (google_id, sender, subject, body_original, received_at, ingested_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        ''', data)
        conn.commit()
        return c.rowcount
    except Exception as e:
        print(f"Error in bulk save: {e}")
        return 0
    finally:
        conn.close()

def get_pending_email() -> Optional[Dict[str, Any]]:
    """Get the oldest pending email."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM emails WHERE status = 'PENDING' ORDER BY ingested_at ASC LIMIT 1")
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def update_email_analysis(email_id: int, redacted_body: str, analysis: Dict[str, Any], suggested_action: str, status: str = 'COMPLETED'):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE emails 
        SET body_redacted = ?, analysis = ?, suggested_action = ?, status = ?, processed_at = ?
        WHERE id = ?
    ''', (redacted_body, json.dumps(analysis), suggested_action, status, datetime.now(), email_id))
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    c = conn.cursor()
    
    # Counts
    c.execute("SELECT status, COUNT(*) FROM emails GROUP BY status")
    counts = dict(c.fetchall())
    
    # Avg Latency (Processed Time - Ingested Time)
    c.execute('''
        SELECT AVG((julianday(processed_at) - julianday(ingested_at)) * 86400.0) 
        FROM emails 
        WHERE status = 'COMPLETED'
    ''')
    avg_latency = c.fetchone()[0]
    
    conn.close()
    
    return {
        "pending": counts.get('PENDING', 0),
        "completed": counts.get('COMPLETED', 0),
        "failed": counts.get('FAILED', 0),
        "avg_latency": round(avg_latency, 2) if avg_latency else 0.0
    }

def get_recent_emails(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM emails ORDER BY ingested_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
