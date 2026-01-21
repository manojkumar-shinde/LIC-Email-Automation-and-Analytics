import csv
import io
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from app.database import get_stats, get_recent_emails, save_email, bulk_save_emails

router = APIRouter()

@router.get("/stats")
def stats():
    return get_stats()

@router.get("/emails")
def emails(limit: int = 50):
    data = get_recent_emails(limit)
    # Parse JSON strings to objects for frontend
    for email in data:
        if email.get('analysis'):
            try:
                email['analysis'] = json.loads(email['analysis'])
            except:
                pass
    return data

@router.post("/ingest")
def manual_ingest(email: dict):
    """Simulate receiving an email (useful for manual testing without Gmail)."""
    # email: { "sender": "...", "subject": "...", "body": "..." }
    fake_id = str(uuid.uuid4())
    success = save_email(
        google_id=fake_id,
        sender=email.get('sender', 'Simulator'),
        subject=email.get('subject', 'No Subject'),
        body=email.get('body', ''),
        received_at=datetime.now()
    )
    if success:
        return {"status": "success", "message": "Email ingested"}
    else:
        raise HTTPException(status_code=400, detail="Failed to ingest (duplicate?)")

@router.post("/ingest/bulk")
async def bulk_ingest(file: UploadFile = File(...)):
    """Simulate receiving multiple emails via file upload (JSON or CSV)."""
    contents = await file.read()
    emails_to_save = []
    
    try:
        decoded = contents.decode('utf-8')
        
        if file.filename.endswith('.json'):
            data = json.loads(decoded)
            if isinstance(data, list):
                for item in data:
                    emails_to_save.append({
                        "google_id": item.get('google_id', str(uuid.uuid4())),
                        "sender": item.get('sender', 'Simulator'),
                        "subject": item.get('subject', 'No Subject'),
                        "body": item.get('body', ''),
                        "received_at": datetime.now()
                    })
            else:
                 raise HTTPException(status_code=400, detail="JSON must be a list of objects")
                 
        elif file.filename.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(decoded))
            for row in reader:
                emails_to_save.append({
                    "google_id": row.get('google_id', str(uuid.uuid4())),
                    "sender": row.get('sender', 'Simulator'),
                    "subject": row.get('subject', 'No Subject'),
                    "body": row.get('body', ''),
                    "received_at": datetime.now()
                })
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .json or .csv")
            
        count = bulk_save_emails(emails_to_save)
        return {"status": "success", "message": f"Ingested {count} emails"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
def export_csv():
    """Stream a CSV export of all completed emails."""
    # We'll just fetch recent for now, ideally fetch ALL
    emails_data = get_recent_emails(limit=1000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Sender', 'Subject', 'Received At', 'Status', 'Intent', 'Sentiment', 'Suggested Action', 'Redacted Body'])
    
    for email in emails_data:
        analysis = {}
        if email.get('analysis'):
            try:
                analysis = json.loads(email['analysis'])
            except:
                pass
                
        writer.writerow([
            email['id'],
            email['sender'],
            email['subject'],
            email['received_at'],
            email['status'],
            analysis.get('intent', ''),
            analysis.get('sentiment', ''),
            email.get('suggested_action', ''),
            email['body_redacted']
        ])
        
    output.seek(0)
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=lic_emails_export.csv"
    return response
