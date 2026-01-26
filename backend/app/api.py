import csv
import io
import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_stats, get_recent_emails, save_email, bulk_save_emails

# Setup Logging
logger = logging.getLogger("API")

router = APIRouter()

# --- Pydantic Models ---
class EmailIngest(BaseModel):
    sender: str = Field(..., description="Email sender address or name")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")

class APIResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[dict] = None

# --- Routes ---

@router.get("/stats", response_model=dict)
def stats():
    try:
        return get_stats()
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/emails")
def emails(page: int = 1, limit: int = 20):
    print(f"DEBUG: EMAILS CALL page={page} limit={limit}", flush=True)
    try:
        result = get_recent_emails(page=page, limit=limit)
        
        # Parse JSON strings to objects for frontend
        for email in result['items']:
            if email.get('analysis'):
                try:
                    email['analysis'] = json.loads(email['analysis'])
                except (json.JSONDecodeError, TypeError):
                    email['analysis'] = {} # Fallback
        return result
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/ingest", response_model=APIResponse)
def manual_ingest(email: EmailIngest):
    """Simulate receiving an email (useful for manual testing without Gmail)."""
    fake_id = str(uuid.uuid4())
    logger.info(f"Manual ingest request: {email.subject}")
    
    success = save_email(
        google_id=fake_id,
        sender=email.sender,
        subject=email.subject,
        body=email.body,
        received_at=datetime.now()
    )
    
    if success:
        return {"status": "success", "message": "Email ingested"}
    else:
        logger.warning(f"Duplicate email rejected: {fake_id}")
        raise HTTPException(status_code=400, detail="Failed to ingest (duplicate?)")

@router.post("/ingest/bulk", response_model=APIResponse)
async def bulk_ingest(file: UploadFile = File(...)):
    """Simulate receiving multiple emails via file upload (JSON or CSV)."""
    logger.info(f"Bulk ingest started: {file.filename}")
    
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        emails_to_save = []
        
        if file.filename.endswith('.json'):
            try:
                data = json.loads(decoded)
            except json.JSONDecodeError:
                 raise HTTPException(status_code=400, detail="Invalid JSON format")
                 
            if isinstance(data, list):
                for item in data:
                    # Validations: Check for body, content, or text keys
                    body = item.get('body') or item.get('content') or item.get('text') or ''
                    if not body or not str(body).strip():
                        continue # Skip empty emails
                        
                    emails_to_save.append({
                        "google_id": item.get('google_id', str(uuid.uuid4())),
                        "sender": item.get('sender', 'Simulator'),
                        "subject": item.get('subject', 'No Subject'),
                        "body": str(body).strip(),
                        "received_at": datetime.now()
                    })
            else:
                 raise HTTPException(status_code=400, detail="JSON must be a list of objects")
                 
        elif file.filename.endswith('.csv'):
            try:
                reader = csv.DictReader(io.StringIO(decoded))
                for i, row in enumerate(reader):
                    # Helper to find key case-insensitively
                    keys = {k.lower(): k for k in row.keys()}
                    
                    # Try to find a body-like column
                    body_key = keys.get('body') or keys.get('content') or keys.get('text') or keys.get('message') or keys.get('description') or keys.get('email_body')
                    
                    body = row[body_key] if body_key else ''
                    
                    # Try to find sender-like column
                    sender_key = keys.get('sender') or keys.get('from') or keys.get('sender_name') or keys.get('sender_email')
                    sender = row[sender_key] if sender_key else 'Simulator'
                    
                    if not body or not str(body).strip():
                         logger.warning(f"Row {i} skipped: Empty body. Keys found: {list(row.keys())}")
                         continue # Skip empty
                         
                    emails_to_save.append({
                        "google_id": row.get('google_id', str(uuid.uuid4())),
                        "sender": sender,
                        "subject": row.get('subject', 'No Subject'),
                        "body": str(body).strip(),
                        "received_at": datetime.now()
                    })
            except csv.Error:
                raise HTTPException(status_code=400, detail="Invalid CSV format")
                
        elif file.filename.endswith('.txt'):
            # Text file support: Each non-empty line is a separate email
            lines = decoded.splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if line:
                    emails_to_save.append({
                        "google_id": str(uuid.uuid4()),
                        "sender": "Text Import",
                        "subject": f"Text Import Batch #{i+1}",
                        "body": line,
                        "received_at": datetime.now()
                    })
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .json, .csv, or .txt")
            
        count = bulk_save_emails(emails_to_save)
        logger.info(f"Bulk ingest complete. Saved {count} emails.")
        return {"status": "success", "message": f"Ingested {count} emails"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/export")
def export_csv():
    """Stream a CSV export of all completed emails."""
    try:
        # We'll just fetch recent for now, ideally fetch ALL (limit=10000)
        result = get_recent_emails(page=1, limit=10000)
        emails_data = result['items']
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['ID', 'Sender', 'Subject', 'Received At', 'Status', 'Intent', 'Confidence', 'Sentiment', 'Summary', 'Generated Reply', 'Redacted Body'])
        
        for email in emails_data:
            analysis = {}
            if email.get('analysis'):
                try:
                    analysis = json.loads(email['analysis'])
                except:
                    pass
            
            # Use suggested_action column for summary as per worker mapping
            summary = email.get('suggested_action', '')
            
            writer.writerow([
                email['id'],
                email['sender'],
                email['subject'],
                email['received_at'],
                email['status'],
                analysis.get('intent', ''),
                analysis.get('confidence', 'N/A'),
                analysis.get('sentiment', ''),
                summary,
                email.get('generated_reply', ''),
                email['body_redacted']
            ])
            
        output.seek(0)
        
        response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=lic_emails_export.csv"
        return response
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Export failed")
