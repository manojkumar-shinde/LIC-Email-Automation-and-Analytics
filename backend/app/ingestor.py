import os.path
import pickle
import time
import base64
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime

from app.database import save_email, init_db

# Setup Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Ingestor")

# Config
# Ideally from env vars
POLL_INTERVAL = 30
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.pickle')

def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.error(f"Corrupt token file: {e}")
            os.remove(TOKEN_FILE)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                return None
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                logger.error("credentials.json not found! Please place it in the backend root.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Failed to auth: {e}")
                return None
                
        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    try:
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"Failed to build service: {e}")
        return None

def decode_body(payload):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body += base64.urlsafe_b64decode(data).decode()
    elif 'body' in payload:
        data = payload['body'].get('data')
        if data:
            body += base64.urlsafe_b64decode(data).decode()
    return body

def fetch_and_save_emails(service):
    """Fetches unread emails and saves them to DB."""
    try:
        results = service.users().messages().list(userId='me', q='is:unread').execute()
        messages = results.get('messages', [])

        if not messages:
            return

        logger.info(f"Found {len(messages)} unread messages.")

        # In a high-volume app, we would use batch requests here.
        # For simplicity and reliability in this refactor, we iterate safely.
        for msg in messages:
            msg_id = msg['id']
            try:
                message = service.users().messages().get(userId='me', id=msg_id).execute()
                payload = message['payload']
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                body = decode_body(payload)
                internal_date = int(message['internalDate']) / 1000
                received_at = datetime.fromtimestamp(internal_date)

                if save_email(msg_id, sender, subject, body, received_at):
                    logger.info(f"Saved email: {subject}")
                    # Mark as read
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                else:
                    logger.info(f"Duplicate email skipped: {msg_id}")
                    # Optionally mark as read anyway to stop processing loop? 
                    # For now, we assume if it's in DB, we should mark read.
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                    
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")

    except Exception as e:
        logger.error(f"An error occurred during fetch: {e}")

def start_loop():
    logger.info("Starting Ingestor Service...")
    # Ideally main.py handles DB init, but ingestor handles its own dependencies if standalone
    init_db() 
    
    while True:
        try:
            service = get_service()
            if service:
                fetch_and_save_emails(service)
            else:
                logger.warning("Gmail service unavailable. Retrying...")
        except KeyboardInterrupt:
            logger.info("Ingestor stopped by user.")
            break
        except Exception as e:
            logger.error(f"Ingestor Loop critical error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    start_loop()
