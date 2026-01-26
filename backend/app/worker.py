import time
import logging
from typing import Optional
from app.database import claim_next_pending_email, update_email_analysis
from app.privacy import redact_pii
from app.brain import analyze_email
from app.priority import compute_priority
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
            confidence=analysis_result.get('confidence', 'Low')
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

def start_loop():
    logger.info("Starting ETL Worker...")
    
    # Exponential Backoff Config
    min_sleep = 2
    max_sleep = 60
    current_sleep = min_sleep
    
    while True:
        try:
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
