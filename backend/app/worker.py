import time
import logging
from typing import Optional
from app.database import (
    claim_next_pending_email, 
    update_email_analysis,
    get_all_gmail_configs,
    bulk_save_emails,
    update_gmail_sync_status,
    increment_gmail_sync_count
)
from app.privacy import redact_pii
from app.brain import analyze_email
from app.priority import compute_priority
from app.gmail_fetcher import GmailAuthenticator, GmailFetcher
from app.reply import generate_reply

# Setup Logging
logger = logging.getLogger("Worker")
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

def process_email() -> bool:
    """
    Claims and processes a single email. 
    Returns True if an email was processed, False otherwise.
    """
    
    # Atomic claim - safe for multiple workers
    email = claim_next_pending_email()
    if not email:
        return False

    logger.info(f"Processing Email ID: {email['id']} - Subject: {email['subject']}")
    
    try:
        # Step 1: Redaction
        original_body = email['body_original']
        # If body is empty, handle gracefully
        if not original_body:
            original_body = ""
            
        redacted_body = redact_pii(original_body)
        
        # Step 2: AI Analysis (RAG)
        analysis_result = analyze_email(redacted_body)
        
        # Step 3: Priority Classification (Rule-based)
        # AI provides context → Rules make decisions
        priority, priority_reason = compute_priority(
            intent=analysis_result.get('intent', ''),
            sentiment=analysis_result.get('sentiment', ''),
            summary=analysis_result.get('summary', ''),
            redacted_body=redacted_body
        )
        
        # Enrich analysis result with priority
        analysis_result['priority'] = priority
        analysis_result['priority_reason'] = priority_reason
        
        logger.info(f"Email {email['id']} - Priority: {priority} ({priority_reason})")
        
        # Step 4: Auto-Reply Generation
        generated_reply = generate_reply(
            email_body=redacted_body,
            intent=analysis_result.get('intent', ''),
            priority=priority,
            confidence=analysis_result.get('confidence', 'Low'),
            sentiment=analysis_result.get('sentiment', 'NEUTRAL')
        )
        
        # Step 5: Save results
        # Mapping new schema (summary, confidence) to DB columns
        # We store 'summary' in 'suggested_action' column to reuse existing schema
        summary = analysis_result.get('summary', 'No summary provided.')
        
        update_email_analysis(
            email_id=email['id'],
            redacted_body=redacted_body,
            analysis=analysis_result, # Stores full JSON (intent, sentiment, summary, confidence, priority)
            suggested_action=summary, # Storing summary here for frontend compatibility
            generated_reply=generated_reply,
            status='COMPLETED'
        )
        logger.info(f"Email {email['id']} completed. Intent: {analysis_result.get('intent')}")
        return True

    except Exception as e:
        logger.error(f"Failed to process email {email['id']}: {e}")
        # Ideally, we should update status to FAILED here to prevent stuck 'PROCESSING' state
        try:
             # Basic failure handling
             update_email_analysis(
                email_id=email['id'],
                redacted_body="",
                analysis={"error": str(e)},
                suggested_action="Manual Intervention",
                status='FAILED'
            )
        except Exception as db_e:
            logger.error(f"Failed to mark email {email['id']} as FAILED: {db_e}")
        return False


# ============================================================================
# GMAIL SYNC FUNCTIONS
# ============================================================================

def sync_gmail_account(gmail_config: dict) -> bool:
    """
    Fetch emails from a Gmail account and save to database.
    
    Args:
        gmail_config: Dictionary from get_gmail_config() with keys:
            - gmail_email: Gmail account email
            - auth_method: 'oauth', 'service_account', or 'token'
            - credentials: Decrypted credentials (token, JSON, or API key)
            
    Returns:
        True if sync succeeded, False otherwise
    """
    gmail_email = gmail_config['gmail_email']
    auth_method = gmail_config['auth_method']
    credentials = gmail_config['credentials']
    
    try:
        logger.info(f"Starting Gmail sync for {gmail_email} ({auth_method})")
        
        # Authenticate based on method
        authenticator = GmailAuthenticator()
        
        if auth_method == 'oauth':
            service = authenticator.authenticate_with_oauth_json(credentials, gmail_email)
        elif auth_method == 'service_account':
            service = authenticator.authenticate_service_account(credentials)
        elif auth_method == 'token':
            service = authenticator.authenticate_with_token(credentials)
        else:
            raise ValueError(f"Unknown auth_method: {auth_method}")
        
        # Create fetcher and get unread emails
        fetcher = GmailFetcher(service)
        emails = fetcher.get_unread_emails(max_results=50)
        
        if not emails:
            logger.info(f"No new emails from {gmail_email}")
            update_gmail_sync_status(gmail_email, 'success', None)
            return True
        
        # Convert Gmail format to database format
        emails_to_save = []
        for email in emails:
            emails_to_save.append({
                'google_id': email['google_id'],
                'sender': email['sender'],
                'subject': email['subject'],
                'body': email['body'],
                'received_at': email['received_at']
            })
        
        # Save to database
        saved_count = bulk_save_emails(emails_to_save)
        
        # Update sync stats
        if saved_count > 0:
            increment_gmail_sync_count(gmail_email, saved_count)
        
        logger.info(f"Gmail sync completed for {gmail_email}: {saved_count} emails saved")
        update_gmail_sync_status(gmail_email, 'success', None)
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gmail sync failed for {gmail_email}: {error_msg}")
        update_gmail_sync_status(gmail_email, 'failed', error_msg)
        return False


def sync_all_gmail_accounts() -> int:
    """
    Sync emails from all enabled Gmail accounts.
    
    Returns:
        Number of accounts successfully synced
    """
    try:
        configs = get_all_gmail_configs(enabled_only=True)
        
        if not configs:
            logger.debug("No enabled Gmail accounts to sync")
            return 0
        
        logger.info(f"Syncing {len(configs)} Gmail account(s)")
        success_count = 0
        
        for config in configs:
            if sync_gmail_account(config):
                success_count += 1
        
        logger.info(f"Gmail sync completed: {success_count}/{len(configs)} accounts successful")
        return success_count
        
    except Exception as e:
        logger.error(f"Error during Gmail sync batch: {e}")
        return 0

def start_loop():
    """
    Main worker loop that continuously:
    1. Syncs emails from configured Gmail accounts
    2. Processes pending emails from database
    
    Uses exponential backoff when no work is available.
    """
    logger.info("Starting ETL Worker...")
    
    # Exponential Backoff Config
    min_sleep = 2
    max_sleep = 60
    current_sleep = min_sleep
    
    # Gmail sync interval (seconds)
    gmail_sync_interval = 300  # Sync Gmail every 5 minutes
    last_gmail_sync = 0
    
    while True:
        try:
            # Check if it's time to sync Gmail
            current_time = time.time()
            if current_time - last_gmail_sync >= gmail_sync_interval:
                logger.debug("Running Gmail sync cycle...")
                sync_all_gmail_accounts()
                last_gmail_sync = current_time
            
            # Process one email from database
            worked = process_email()
            
            if worked:
                # Reset backoff on success
                current_sleep = min_sleep
            else:
                # No work - sleep and backoff
                time.sleep(current_sleep)
                current_sleep = min(current_sleep * 1.5, max_sleep)
                
        except KeyboardInterrupt:
            logger.info("Worker stopped by user.")
            break
        except Exception as e:
            logger.error(f"Worker Loop Error: {e}")
            time.sleep(5) 

if __name__ == '__main__':
    start_loop()
