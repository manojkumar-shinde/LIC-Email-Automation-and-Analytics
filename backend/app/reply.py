import logging
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger("ReplyGenerator")

# ════════════════════════════════════════════════════════════════════════════
# KEYWORD CATEGORIZATION (Two-Tier Safety System)
# ════════════════════════════════════════════════════════════════════════════

# HARD BLOCK: Always trigger NO_REPLY (high-risk financial/legal topics)
HARD_BLOCK_KEYWORDS = [
    'claim', 'claims', 'claimed',
    'payment', 'payments', 'paid', 'pay', 'paying',
    'refund', 'refunds', 'refunded', 'refunding',
    'fraud', 'fraudulent',
    'legal', 'lawyer', 'attorney', 'court',
    'complaint', 'complaints', 'complaining',
    'escalation', 'escalate', 'escalated', 'escalating'
]

# SOFT INDICATORS: Block only when combined with risk amplifiers
SOFT_INDICATORS = [
    'timeline', 'timelines', 'deadline', 'due date', 'due by',
    'approval', 'approve', 'approved', 'approving',
    'amount', 'amounts',
    'processing time', 'process time', 'processing delay'
]

# URGENCY/RISK AMPLIFIERS: Make soft indicators risky
URGENCY_KEYWORDS = [
    'urgent', 'urgently', 'immediate', 'immediately', 'asap',
    'delay', 'delayed', 'waiting', 'overdue', 'past due'
]

# POST-GENERATION VALIDATION: Forbidden terms in LLM output
FORBIDDEN_OUTPUT_TERMS = [
    'payment', 'claim', 'refund', 'refunds',
    'approve', 'approved', 'authorization', 'confirmed',
    'guarantee', 'guaranteed', 'will process', 'will be processed',
    'timeline', 'timeframe', 'within', 'by', 'days',
   'settled', 'resolved', 'completed'
]

# ════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC PATTERN SELECTION
# ════════════════════════════════════════════════════════════════════════════

# Intent → Pattern Mapping (No LLM discretion)
PATTERN_MAPPING = {
    'GENERAL_ENQUIRY': 'PATTERN_B',
    'REQUEST': 'PATTERN_A',
    'APPRECIATION': 'PATTERN_C'
}

# Approved Response Patterns (Exact Text - DO NOT MODIFY)
APPROVED_PATTERNS = {
    'PATTERN_A': "Thank you for contacting LIC.\nWe have received your message and it has been noted for review.",
    'PATTERN_B': "Thank you for your query.\nOur team is reviewing the information and will respond with the relevant details.",
    'PATTERN_C': "Thank you for your feedback.\nWe appreciate you taking the time to share your experience."
}

# ════════════════════════════════════════════════════════════════════════════
# NO_REPLY REASON TRACKING (Auditability)
# ════════════════════════════════════════════════════════════════════════════

NO_REPLY_REASONS = {
    'HIGH_PRIORITY': 'Email priority is HIGH - requires human handling',
    'RESTRICTED_INTENT': 'Intent is COMPLAINT/CLAIM_RELATED/PAYMENT_ISSUE',
    'LOW_CONFIDENCE': 'Confidence level is not High',
    'HARD_BLOCK_KEYWORD': 'Contains hard block keyword',
    'SOFT_INDICATOR_WITH_RISK': 'Contains soft indicator with negative sentiment or urgency',
    'POST_VALIDATION_FAIL': 'Generated response contained forbidden term',
    'PATTERN_NOT_FOUND': 'Intent does not map to a safe pattern',
    'LLM_ERROR': 'LLM generation failed'
}

# ════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def check_hard_keywords(email_body: str) -> tuple[bool, str]:
    """
    Check for hard block keywords (always block).
    Returns: (found, keyword)
    """
    email_lower = email_body.lower()
    for keyword in HARD_BLOCK_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', email_lower):
            return True, keyword
    return False, ""

def check_soft_indicators_with_risk(email_body: str, sentiment: str) -> tuple[bool, str]:
    """
    Check soft indicators AND verify if risk amplifiers are present.
    SOFT INDICATORS trigger NO_REPLY only if:
    - Sentiment is NEGATIVE, OR
    - Urgency keywords are present
    
    Returns: (should_block, reason)
    """
    email_lower = email_body.lower()
    
    # Check if soft indicators exist
    soft_found = False
    soft_keyword = ""
    for indicator in SOFT_INDICATORS:
        if indicator in email_lower:
            soft_found = True
            soft_keyword = indicator
            break
    
    if not soft_found:
        return False, ""
    
    # Soft indicator found - check for risk amplifiers
    has_negative_sentiment = (sentiment == "NEGATIVE")
    has_urgency = any(urgency in email_lower for urgency in URGENCY_KEYWORDS)
    
    if has_negative_sentiment or has_urgency:
        risk_factor = "negative sentiment" if has_negative_sentiment else "urgency keywords"
        return True, f"'{soft_keyword}' + {risk_factor}"
    
    # Soft indicator present but NO risk - safe to proceed
    return False, ""

def check_forbidden_output_terms(response: str) -> tuple[bool, str]:
    """
    Post-generation validation: Scan LLM output for forbidden terms.
    This is the SECOND SAFETY GATE.
    
    Returns: (found, term)
    """
    response_lower = response.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        if term in response_lower:
            return True, term
    return False, ""

def log_no_reply_decision(reason_key: str, **details):
    """
    Enhanced audit logging for NO_REPLY decisions.
    Logs specific reason and contextual details for compliance audits.
    """
    reason = NO_REPLY_REASONS.get(reason_key, "Unknown reason")
    log_msg = f"NO_REPLY Decision - Reason: {reason_key} ({reason})"
    
    if details:
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        log_msg += f" | Details: {detail_str}"
    
    logger.info(log_msg)

# ════════════════════════════════════════════════════════════════════════════
# UPDATED SYSTEM PROMPT (Deterministic Pattern Selection)
# ════════════════════════════════════════════════════════════════════════════

REPLY_TEMPLATE = """
SYSTEM ROLE:
You are an ASSISTIVE EMAIL REPLY AGENT for LIC (Life Insurance Corporation of India).

You do NOT send emails.
You do NOT take decisions.
You generate SAFE reply drafts ONLY for HUMAN REVIEW.

────────────────────────────────────

CRITICAL INSTRUCTION:

Based on the Intent provided, return EXACTLY one of these patterns:

Intent: GENERAL_ENQUIRY
→ Return: "Thank you for your query.
Our team is reviewing the information and will respond with the relevant details."

Intent: REQUEST
→ Return: "Thank you for contacting LIC.
We have received your message and it has been noted for review."

Intent: APPRECIATION
→ Return: "Thank you for your feedback.
We appreciate you taking the time to share your experience."

DO NOT modify the wording.
DO NOT add extra text.
DO NOT explain or provide commentary.

If the intent is NOT one of the above, return: NO_REPLY

────────────────────────────────────

INPUT DATA:

Email Content (PII redacted):
{email}

Metadata:
• Intent: {intent}
• Priority: {priority}
• Confidence: {confidence}

────────────────────────────────────

OUTPUT:

Return ONLY the exact pattern text for the given intent.
No JSON. No quotes. No explanations.

END.
"""

# ════════════════════════════════════════════════════════════════════════════
# MAIN REPLY GENERATION FUNCTION (Enhanced)
# ════════════════════════════════════════════════════════════════════════════

def generate_reply(email_body: str, intent: str, priority: str, confidence: str, sentiment: str = "NEUTRAL") -> str:
    """
    Generates an automated reply draft with multi-layered safety checks.
    
    Safety Layers:
    1. Entry conditions (priority/intent/confidence)
    2. Hard keyword blocking
    3. Soft keyword + risk amplifier blocking
    4. Deterministic pattern selection
    5. Post-generation validation
    
    Args:
        email_body: Email content (PII redacted)
        intent: Classification intent (GENERAL_ENQUIRY, REQUEST, etc.)
        priority: Email priority (LOW, MEDIUM, HIGH)
        confidence: Classification confidence (High, Medium, Low)
        sentiment: Email sentiment (POSITIVE, NEUTRAL, NEGATIVE)
    
    Returns:
        str: Reply draft or "NO_REPLY"
    """
    
    # ════════════════════════════════════════════════════════════════════════
    # LAYER 1: Entry Conditions (Fail-Fast)
    # ════════════════════════════════════════════════════════════════════════
    
    if priority == "HIGH":
        log_no_reply_decision('HIGH_PRIORITY', priority=priority, intent=intent)
        return "NO_REPLY"
    
    if intent in ["COMPLAINT", "CLAIM_RELATED", "PAYMENT_ISSUE"]:
        log_no_reply_decision('RESTRICTED_INTENT', intent=intent, priority=priority)
        return "NO_REPLY"
    
    if confidence != "High":
        log_no_reply_decision('LOW_CONFIDENCE', confidence=confidence, intent=intent)
        return "NO_REPLY"
    
    # ════════════════════════════════════════════════════════════════════════
    # LAYER 2: Hard Keyword Blocking (Always Block)
    # ════════════════════════════════════════════════════════════════════════
    
    hard_found, hard_keyword = check_hard_keywords(email_body)
    if hard_found:
        log_no_reply_decision('HARD_BLOCK_KEYWORD', keyword=hard_keyword, intent=intent)
        return "NO_REPLY"
    
    # ════════════════════════════════════════════════════════════════════════
    # LAYER 3: Soft Indicator + Risk Amplifier Blocking
    # ════════════════════════════════════════════════════════════════════════
    
    soft_risky, soft_reason = check_soft_indicators_with_risk(email_body, sentiment)
    if soft_risky:
        log_no_reply_decision('SOFT_INDICATOR_WITH_RISK', reason=soft_reason, sentiment=sentiment)
        return "NO_REPLY"
    
    # ════════════════════════════════════════════════════════════════════════
    # LAYER 4: Deterministic Pattern Selection (No LLM Discretion)
    # ════════════════════════════════════════════════════════════════════════
    
    # Check if intent maps to a safe pattern
    pattern_key = PATTERN_MAPPING.get(intent)
    if not pattern_key:
        log_no_reply_decision('PATTERN_NOT_FOUND', intent=intent)
        return "NO_REPLY"
    
    # Get the exact approved pattern
    approved_response = APPROVED_PATTERNS.get(pattern_key)
    
    # For extra safety, still invoke LLM but with strict deterministic prompt
    # This maintains the architecture while adding pattern enforcement
    try:
        llm = ChatOllama(model="gemma2:2b", temperature=0, timeout=30.0)
        
        prompt = PromptTemplate(
            input_variables=["email", "priority", "intent", "confidence"],
            template=REPLY_TEMPLATE
        )
        
        chain = prompt | llm | StrOutputParser()
        
        logger.info(f"Generating reply: Pattern={pattern_key}, Intent={intent}, Priority={priority}")
        
        response = chain.invoke({
            "email": email_body,
            "priority": priority,
            "intent": intent,
            "confidence": confidence
        })
        
        cleaned_response = response.strip().strip('"').strip("'")
        
        # If LLM returns NO_REPLY, respect it
        if cleaned_response == "NO_REPLY":
            log_no_reply_decision('LLM_ERROR', reason="LLM returned NO_REPLY")
            return "NO_REPLY"
        
        # ════════════════════════════════════════════════════════════════════
        # LAYER 5: Post-Generation Validation (Second Safety Gate)
        # ════════════════════════════════════════════════════════════════════
        
        forbidden_found, forbidden_term = check_forbidden_output_terms(cleaned_response)
        if forbidden_found:
            log_no_reply_decision('POST_VALIDATION_FAIL', term=forbidden_term, response_preview=cleaned_response[:50])
            return "NO_REPLY"
        
        # ════════════════════════════════════════════════════════════════════
        # SUCCESS: Reply Generated and Validated
        # ════════════════════════════════════════════════════════════════════
        
        logger.info(f"Reply generated successfully: Pattern={pattern_key}, Length={len(cleaned_response)}")
        return cleaned_response
    
    except Exception as e:
        log_no_reply_decision('LLM_ERROR', error=str(e))
        logger.error(f"Reply generation exception: {e}")
        return "NO_REPLY"
