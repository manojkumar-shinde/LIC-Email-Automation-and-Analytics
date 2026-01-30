import csv
import io
import uuid
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.database import (
    get_stats, 
    get_recent_emails, 
    save_email, 
    bulk_save_emails,
    save_gmail_config,
    get_gmail_config,
    get_all_gmail_configs,
    toggle_gmail_sync,
    delete_gmail_config,
    get_gmail_config_stats
)
from app.worker import sync_all_gmail_accounts, sync_gmail_account

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

class GmailConnectRequest(BaseModel):
    gmail_email: str = Field(..., description="Gmail account email address")
    auth_method: str = Field(default="token", description="Authentication method: 'oauth', 'service_account', or 'token'")
    api_key: Optional[str] = Field(None, description="API key/token or JSON credentials (depending on auth_method)")
    
class GmailSyncResponse(BaseModel):
    status: str
    message: str
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


# ============================================================================
# GMAIL API ENDPOINTS
# ============================================================================

@router.post("/gmail/connect", response_model=APIResponse)
def gmail_connect(request: GmailConnectRequest):
    """
    Connect a Gmail account to the platform.
    Saves encrypted credentials for later syncing.
    
    Request body:
    {
        "gmail_email": "user@gmail.com",
        "auth_method": "token",  # or "oauth", "service_account"
        "api_key": "ya29.a0AUMWg_Kkdj6I8XgU8QoGq5..."
    }
    
    Returns:
    {
        "status": "success",
        "message": "Gmail account connected",
        "data": {
            "gmail_email": "user@gmail.com",
            "auth_method": "token",
            "sync_enabled": true,
            "last_sync_time": null
        }
    }
    """
    try:
        # Validate inputs
        if not request.gmail_email or "@" not in request.gmail_email:
            raise HTTPException(status_code=400, detail="Invalid Gmail email address")
        
        if not request.api_key:
            raise HTTPException(status_code=400, detail="API key/credentials required")
        
        if request.auth_method not in ["oauth", "service_account", "token"]:
            raise HTTPException(status_code=400, detail="Invalid auth_method. Use 'oauth', 'service_account', or 'token'")
        
        # Save Gmail config (credentials will be encrypted)
        success = save_gmail_config(
            gmail_email=request.gmail_email,
            auth_method=request.auth_method,
            credentials=request.api_key
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save Gmail configuration")
        
        # Retrieve and return the saved config (without credentials)
        config = get_gmail_config(request.gmail_email)
        if not config:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved configuration")
        
        # Remove sensitive data from response
        response_data = {
            "gmail_email": config['gmail_email'],
            "auth_method": config['auth_method'],
            "sync_enabled": config['sync_enabled'],
            "last_sync_time": config['last_sync_time'],
            "last_sync_status": config['last_sync_status'],
            "total_synced": config['total_synced']
        }
        
        logger.info(f"Gmail account connected: {request.gmail_email}")
        
        return {
            "status": "success",
            "message": f"Gmail account '{request.gmail_email}' connected successfully",
            "data": response_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Gmail account: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/gmail/sync", response_model=GmailSyncResponse)
async def gmail_sync(gmail_email: Optional[str] = None, background_tasks: BackgroundTasks = None):
    """
    Manually trigger Gmail sync for a specific account or all accounts.
    
    Query parameters:
    - gmail_email (optional): Specific Gmail email to sync. If omitted, syncs all enabled accounts.
    
    Returns:
    {
        "status": "syncing",
        "message": "Gmail sync started in background",
        "data": {
            "accounts_syncing": 1,
            "last_sync": "2026-01-24T15:30:00"
        }
    }
    """
    try:
        current_time = datetime.now()
        
        if gmail_email:
            # Sync specific account
            config = get_gmail_config(gmail_email)
            if not config:
                raise HTTPException(status_code=404, detail=f"Gmail account '{gmail_email}' not found")
            
            # Run sync in background
            background_tasks.add_task(sync_gmail_account, config)
            
            return {
                "status": "syncing",
                "message": f"Sync started for {gmail_email}",
                "data": {
                    "accounts_syncing": 1,
                    "last_sync": current_time.isoformat()
                }
            }
        else:
            # Sync all enabled accounts
            configs = get_all_gmail_configs(enabled_only=True)
            if not configs:
                return {
                    "status": "success",
                    "message": "No enabled Gmail accounts to sync",
                    "data": {
                        "accounts_syncing": 0,
                        "last_sync": current_time.isoformat()
                    }
                }
            
            # Run sync in background
            background_tasks.add_task(sync_all_gmail_accounts)
            
            return {
                "status": "syncing",
                "message": f"Sync started for {len(configs)} account(s)",
                "data": {
                    "accounts_syncing": len(configs),
                    "last_sync": current_time.isoformat()
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering Gmail sync: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/gmail/accounts", response_model=APIResponse)
def gmail_accounts():
    """
    Get list of all connected Gmail accounts and their sync status.
    
    Returns:
    {
        "status": "success",
        "data": {
            "accounts": [
                {
                    "gmail_email": "user@gmail.com",
                    "auth_method": "token",
                    "sync_enabled": true,
                    "last_sync_time": "2026-01-24T15:30:00",
                    "last_sync_status": "success",
                    "total_synced": 42
                }
            ],
            "stats": {
                "total_accounts": 1,
                "enabled_accounts": 1,
                "successful_syncs": 5,
                "total_emails_synced": 42
            }
        }
    }
    """
    try:
        accounts = get_all_gmail_configs(enabled_only=False)
        stats = get_gmail_config_stats()
        
        # Remove sensitive data
        safe_accounts = []
        for account in accounts:
            safe_accounts.append({
                "gmail_email": account['gmail_email'],
                "auth_method": account['auth_method'],
                "sync_enabled": account['sync_enabled'],
                "last_sync_time": account['last_sync_time'],
                "last_sync_status": account['last_sync_status'],
                "last_sync_error": account['last_sync_error'],
                "total_synced": account['total_synced']
            })
        
        return {
            "status": "success",
            "message": "Retrieved Gmail accounts",
            "data": {
                "accounts": safe_accounts,
                "stats": stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving Gmail accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/gmail/toggle", response_model=APIResponse)
def gmail_toggle(gmail_email: str, enabled: bool):
    """
    Enable or disable sync for a Gmail account.
    
    Query parameters:
    - gmail_email: Gmail email address
    - enabled: true/false
    
    Returns:
    {
        "status": "success",
        "message": "Sync toggled for user@gmail.com",
        "data": {
            "gmail_email": "user@gmail.com",
            "sync_enabled": true
        }
    }
    """
    try:
        # Verify account exists
        config = get_gmail_config(gmail_email)
        if not config:
            raise HTTPException(status_code=404, detail=f"Gmail account '{gmail_email}' not found")
        
        # Toggle sync
        success = toggle_gmail_sync(gmail_email, enabled)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update sync status")
        
        return {
            "status": "success",
            "message": f"Sync {'enabled' if enabled else 'disabled'} for {gmail_email}",
            "data": {
                "gmail_email": gmail_email,
                "sync_enabled": enabled
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling Gmail sync: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/gmail/disconnect", response_model=APIResponse)
def gmail_disconnect(gmail_email: str):
    """
    Disconnect and remove a Gmail account configuration.
    
    Query parameters:
    - gmail_email: Gmail email address to disconnect
    
    Returns:
    {
        "status": "success",
        "message": "Gmail account disconnected"
    }
    """
    try:
        # Verify account exists
        config = get_gmail_config(gmail_email)
        if not config:
            raise HTTPException(status_code=404, detail=f"Gmail account '{gmail_email}' not found")
        
        # Delete config
        success = delete_gmail_config(gmail_email)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete Gmail configuration")
        
        logger.info(f"Gmail account disconnected: {gmail_email}")
        
        return {
            "status": "success",
            "message": f"Gmail account '{gmail_email}' disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Gmail account: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# GMAIL OAUTH 2.0 ENDPOINTS
# ============================================================================

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly'
]
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'  # For installed apps


@router.get("/gmail/oauth/authorize")
def gmail_oauth_authorize(gmail_email: str):
    """
    Start OAuth 2.0 authorization flow for Gmail.
    
    Query parameters:
    - gmail_email: Gmail account email address to connect
    
    Returns authorization URL for user to visit.
    
    Returns:
    {
        "status": "success",
        "message": "Visit authorization URL",
        "data": {
            "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
        }
    }
    """
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            raise HTTPException(
                status_code=500, 
                detail=f"OAuth credentials file not found at {CREDENTIALS_FILE}. Please add credentials.json"
            )
        
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent to get refresh_token
            login_hint=gmail_email
        )
        
        logger.info(f"Generated OAuth URL for {gmail_email}")
        
        return {
            "status": "success",
            "message": f"Visit the authorization URL to grant access for {gmail_email}",
            "data": {
                "auth_url": auth_url,
                "gmail_email": gmail_email,
                "instructions": "1. Visit the auth_url, 2. Authorize the app, 3. Copy the authorization code, 4. Call /gmail/oauth/callback with the code"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")


class OAuthCallbackRequest(BaseModel):
    gmail_email: str = Field(..., description="Gmail account email address")
    auth_code: str = Field(..., description="Authorization code from OAuth redirect")


@router.post("/gmail/oauth/callback")
def gmail_oauth_callback(request: OAuthCallbackRequest):
    """
    Complete OAuth 2.0 flow by exchanging authorization code for tokens.
    
    Request body:
    {
        "gmail_email": "user@gmail.com",
        "auth_code": "4/0AfJohXk..."
    }
    
    Returns:
    {
        "status": "success",
        "message": "Gmail account connected successfully with OAuth",
        "data": {
            "gmail_email": "user@gmail.com",
            "has_refresh_token": true,
            "token_expires_at": "2024-01-28T10:30:00"
        }
    }
    """
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            raise HTTPException(
                status_code=500,
                detail="OAuth credentials file not found"
            )
        
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=request.auth_code)
        
        # Get credentials object
        creds = flow.credentials
        
        if not creds:
            raise HTTPException(status_code=500, detail="Failed to obtain credentials")
        
        # Build credentials JSON with refresh token
        creds_dict = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None
        }
        
        # Save to database (credentials stored as encrypted JSON)
        success = save_gmail_config(
            gmail_email=request.gmail_email,
            auth_method='oauth',
            credentials=json.dumps(creds_dict)
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save Gmail configuration")
        
        logger.info(f"OAuth tokens saved for {request.gmail_email}")
        
        # Update database with refresh token and expiry separately
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emails.db")
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                UPDATE gmail_config 
                SET refresh_token = ?, token_expiry = ?
                WHERE gmail_email = ?
            """, (creds.refresh_token, creds.expiry.isoformat() if creds.expiry else None, request.gmail_email))
            conn.commit()
        finally:
            conn.close()
        
        return {
            "status": "success",
            "message": f"Gmail account '{request.gmail_email}' connected successfully with OAuth",
            "data": {
                "gmail_email": request.gmail_email,
                "auth_method": "oauth",
                "has_refresh_token": bool(creds.refresh_token),
                "token_expires_at": creds.expiry.isoformat() if creds.expiry else None,
                "scopes": creds.scopes
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")

