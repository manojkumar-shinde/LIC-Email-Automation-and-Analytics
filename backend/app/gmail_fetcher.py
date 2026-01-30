"""
Gmail API Integration Module
Handles fetching emails from Gmail using Google API Client
Supports both OAuth 2.0 and Service Account authentication
"""

import logging
import base64
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Optional OAuth imports (not required for token-based auth)
try:
    from google.auth.oauthlib.flow import InstalledAppFlow
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False
    InstalledAppFlow = None

# Setup Logging
logger = logging.getLogger("GmailFetcher")

# Gmail API scope
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailAuthenticator:
    """Handle Gmail API authentication (OAuth 2.0 and Service Account)"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize Gmail authenticator.
        
        Args:
            credentials_path: Path to credentials.json (from Google Cloud Console)
            token_path: Path to store OAuth tokens (default: .gmail_token.pickle)
        """
        self.credentials_path = credentials_path
        self.token_path = token_path or ".gmail_token.pickle"
        self.service = None
    
    def authenticate_oauth(self) -> Any:
        """
        Authenticate using OAuth 2.0 (User login).
        User will be prompted to log in and grant permissions.
        
        Returns:
            Gmail service object
        """
        if not HAS_OAUTH:
            raise RuntimeError("OAuth not available. Install google-auth-oauthlib: pip install google-auth-oauthlib")
        
        try:
            import pickle
            import os
            
            # Check if token already exists
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token_file:
                    creds = pickle.load(token_file)
                    if creds and creds.valid:
                        logger.info("Using existing OAuth token")
                        self.service = build('gmail', 'v1', credentials=creds)
                        return self.service
            
            # Create new OAuth flow
            if not self.credentials_path:
                raise ValueError("credentials_path required for OAuth authentication")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open(self.token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)
            
            logger.info("OAuth authentication successful")
            self.service = build('gmail', 'v1', credentials=creds)
            return self.service
            
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            raise
    
    def authenticate_service_account(self, service_account_json: str) -> Any:
        """
        Authenticate using Service Account (for shared/admin mailboxes).
        
        Args:
            service_account_json: Path to service account JSON file or JSON string
            
        Returns:
            Gmail service object
        """
        try:
            # Load service account credentials
            if service_account_json.startswith('{'):
                # JSON string provided
                creds_dict = json.loads(service_account_json)
            else:
                # File path provided
                with open(service_account_json, 'r') as f:
                    creds_dict = json.load(f)
            
            # Create credentials
            creds = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=SCOPES
            )
            
            logger.info("Service Account authentication successful")
            self.service = build('gmail', 'v1', credentials=creds)
            return self.service
            
        except Exception as e:
            logger.error(f"Service Account authentication failed: {e}")
            raise
    
    def authenticate_with_token(self, access_token: str) -> Any:
        """
        Authenticate using a pre-generated access token.
        
        Args:
            access_token: OAuth 2.0 access token
            
        Returns:
            Gmail service object
        """
        try:
            creds = OAuth2Credentials(token=access_token)
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Token authentication successful")
            return self.service
        except Exception as e:
            logger.error(f"Token authentication failed: {e}")
            raise
    
    def authenticate_with_oauth_json(self, creds_json: str, gmail_email: str) -> Any:
        """
        Authenticate using OAuth credentials JSON (with refresh token support).
        Automatically refreshes expired tokens.
        
        Args:
            creds_json: JSON string containing OAuth credentials
            gmail_email: Gmail account email (for database updates)
            
        Returns:
            Gmail service object
        """
        try:
            import json
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from datetime import datetime
            import sqlite3
            import os
            
            # Parse credentials JSON
            creds_dict = json.loads(creds_json)
            
            # Create Credentials object
            creds = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes')
            )
            
            # Set expiry if available
            if creds_dict.get('expiry'):
                from datetime import datetime
                creds.expiry = datetime.fromisoformat(creds_dict['expiry'])
            
            # Check if token needs refresh
            if creds.expired and creds.refresh_token:
                logger.info(f"Access token expired for {gmail_email}, refreshing...")
                creds.refresh(Request())
                logger.info(f"Token refreshed successfully for {gmail_email}")
                
                # Update database with new tokens
                updated_creds = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None
                }
                
                # Save refreshed credentials back to database
                from app.database import save_gmail_config
                save_gmail_config(gmail_email, 'oauth', json.dumps(updated_creds))
                
                # Update token_expiry column
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emails.db")
                conn = sqlite3.connect(db_path)
                try:
                    conn.execute("""
                        UPDATE gmail_config 
                        SET token_expiry = ?
                        WHERE gmail_email = ?
                    """, (creds.expiry.isoformat() if creds.expiry else None, gmail_email))
                    conn.commit()
                finally:
                    conn.close()
                
                logger.info(f"Updated credentials saved for {gmail_email}")
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info(f"OAuth authentication successful for {gmail_email}")
            return self.service
            
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            raise



class GmailFetcher:
    """Fetch and parse emails from Gmail"""
    
    def __init__(self, service: Any):
        """
        Initialize Gmail Fetcher.
        
        Args:
            service: Gmail API service object (from GmailAuthenticator)
        """
        self.service = service
    
    def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch (default: 10)
            
        Returns:
            List of email dictionaries with keys:
            - google_id: Unique Gmail message ID
            - sender: Sender email address
            - subject: Email subject
            - body: Email body (plain text or HTML)
            - received_at: Email timestamp
        """
        try:
            logger.info(f"Fetching {max_results} unread emails...")
            
            # Search for unread emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread emails")
            
            emails = []
            for message in messages:
                email_data = self._parse_message(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            raise
        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
            raise
    
    def get_emails_since(self, since_timestamp: datetime, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch emails received after a specific timestamp.
        
        Args:
            since_timestamp: Datetime to fetch emails from
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        try:
            # Convert timestamp to Gmail query format (Unix timestamp)
            unix_timestamp = int(since_timestamp.timestamp())
            
            logger.info(f"Fetching emails since {since_timestamp}...")
            
            results = self.service.users().messages().list(
                userId='me',
                q=f'after:{unix_timestamp}',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails since {since_timestamp}")
            
            emails = []
            for message in messages:
                email_data = self._parse_message(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails since timestamp: {e}")
            raise
    
    def get_all_emails(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all emails from Gmail inbox.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        try:
            logger.info(f"Fetching all emails (limit: {max_results})...")
            
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails")
            
            emails = []
            for message in messages:
                email_data = self._parse_message(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching all emails: {e}")
            raise
    
    def _parse_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Gmail message and extract relevant data.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary with email data or None if parsing fails
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            
            # Extract header fields
            sender = self._get_header_value(headers, 'From')
            subject = self._get_header_value(headers, 'Subject')
            date_str = self._get_header_value(headers, 'Date')
            
            # Parse email body
            body = self._get_email_body(message['payload'])
            
            # Parse date
            received_at = self._parse_email_date(date_str)
            
            return {
                'google_id': message_id,
                'sender': sender,
                'subject': subject,
                'body': body,
                'received_at': received_at
            }
            
        except Exception as e:
            logger.warning(f"Error parsing message {message_id}: {e}")
            return None
    
    def _get_header_value(self, headers: List[Dict], header_name: str) -> str:
        """Extract value from email headers."""
        for header in headers:
            if header['name'].lower() == header_name.lower():
                return header['value']
        return ""
    
    def _get_email_body(self, payload: Dict) -> str:
        """
        Extract email body (handles both plain text and HTML).
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Email body as string
        """
        try:
            if 'parts' in payload:
                # Multipart message - extract text/plain or text/html
                for part in payload['parts']:
                    mime_type = part.get('mimeType', '')
                    
                    if mime_type == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    
                    elif mime_type == 'text/html':
                        data = part['body'].get('data', '')
                        if data:
                            # Return HTML as-is; consider converting to plain text if needed
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                # Simple message
                data = payload['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting email body: {e}")
            return ""
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """
        Parse email date string to datetime.
        Gmail returns dates in RFC 2822 format.
        
        Args:
            date_str: Date string from email header
            
        Returns:
            Parsed datetime or current time if parsing fails
        """
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}, using current time")
            return datetime.now()


# Helper function for quick setup
def setup_gmail_fetcher(auth_method: str = 'oauth', 
                       credentials_path: str = None,
                       service_account_json: str = None,
                       access_token: str = None) -> GmailFetcher:
    """
    Quick setup function for Gmail Fetcher.
    
    Args:
        auth_method: 'oauth', 'service_account', or 'token'
        credentials_path: Path to credentials.json (for OAuth)
        service_account_json: Path or JSON string of service account
        access_token: Pre-generated access token
        
    Returns:
        GmailFetcher instance ready to use
        
    Example:
        # OAuth method
        fetcher = setup_gmail_fetcher('oauth', 'credentials.json')
        emails = fetcher.get_unread_emails(5)
        
        # Service Account method
        fetcher = setup_gmail_fetcher('service_account', service_account_json='sa.json')
        emails = fetcher.get_all_emails()
    """
    authenticator = GmailAuthenticator(credentials_path=credentials_path)
    
    if auth_method == 'oauth':
        service = authenticator.authenticate_oauth()
    elif auth_method == 'service_account':
        if not service_account_json:
            raise ValueError("service_account_json required for service_account auth_method")
        service = authenticator.authenticate_service_account(service_account_json)
    elif auth_method == 'token':
        if not access_token:
            raise ValueError("access_token required for token auth_method")
        service = authenticator.authenticate_with_token(access_token)
    else:
        raise ValueError(f"Unknown auth_method: {auth_method}")
    
    return GmailFetcher(service)
