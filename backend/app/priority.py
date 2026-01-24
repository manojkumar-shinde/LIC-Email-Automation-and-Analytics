"""
Email Priority Classification Engine

This module implements a deterministic, rule-based priority classification system
for emails based on AI analysis outputs (intent, sentiment, summary).

DESIGN PRINCIPLE:
    AI understands context → Rules make decisions

The LLM provides semantic understanding (intent, sentiment, summary).
This module uses those outputs to make deterministic priority decisions.

PRIORITY LEVELS:
    - HIGH: Urgent issues requiring immediate attention
    - MEDIUM: Standard servicing requests
    - LOW: Informational or non-actionable emails

INPUTS:
    - intent: Email intent from AI (e.g., COMPLAINT, CLAIM_RELATED, etc.)
    - sentiment: Sentiment from AI (POSITIVE, NEGATIVE, NEUTRAL)
    - summary: AI-generated summary of the email
    - redacted_body: (Optional) Redacted email body for keyword analysis

OUTPUT:
    - Tuple of (priority_level, explanation)
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger("Priority")

# High-priority keywords indicating urgency, escalation, or critical issues
HIGH_PRIORITY_KEYWORDS = [
    # Urgency indicators
    "urgent", "emergency", "immediately", "asap", "critical",
    
    # Complaint escalation
    "complaint", "grievance", "escalation", "escalate",
    
    # Financial/claim issues
    "delay", "delayed", "not received", "haven't received", "didn't receive",
    "non-payment", "unpaid", "overdue", "pending payment",
    
    # Legal/fraud
    "legal", "lawyer", "attorney", "court", "fraud", "fraudulent",
    "police", "fir", "consumer forum",
    
    # Death claims (especially urgent in insurance)
    "death", "died", "passed away", "demise", "deceased",
    
    # Severe issues
    "refund", "cancel", "cancellation", "terminate", "reject", "rejected"
]

# Medium-priority keywords (informational but important)
MEDIUM_PRIORITY_KEYWORDS = [
    "status", "update", "information", "enquiry", "inquiry",
    "policy", "premium", "maturity", "benefit",
    "change", "modify", "amendment"
]


def _contains_keywords(text: str, keywords: list) -> Tuple[bool, str]:
    """
    Check if text contains any of the given keywords (case-insensitive).
    Returns (found, matched_keyword).
    """
    if not text:
        return False, ""
    
    text_lower = text.lower()
    for keyword in keywords:
        # Use word boundary matching to avoid false positives
        # e.g., "delay" should match "delayed" but not "display"
        pattern = r'\b' + re.escape(keyword.lower())
        if re.search(pattern, text_lower):
            return True, keyword
    
    return False, ""


def compute_priority(
    intent: str,
    sentiment: str,
    summary: str,
    redacted_body: str = ""
) -> Tuple[str, str]:
    """
    Compute email priority based on AI analysis outputs.
    
    This is a pure function: same inputs always produce same outputs.
    No randomness, no ML models, 100% deterministic and auditable.
    
    Args:
        intent: Email intent from AI (COMPLAINT, CLAIM_RELATED, etc.)
        sentiment: Sentiment from AI (POSITIVE, NEGATIVE, NEUTRAL)
        summary: AI-generated summary
        redacted_body: (Optional) Redacted email body
    
    Returns:
        Tuple of (priority_level, explanation)
        - priority_level: "HIGH" | "MEDIUM" | "LOW"
        - explanation: Human-readable justification
    
    Examples:
        >>> compute_priority("COMPLAINT", "NEGATIVE", "Customer angry about claim delay")
        ('HIGH', 'Intent: COMPLAINT, Sentiment: NEGATIVE, Keyword: delay')
        
        >>> compute_priority("APPRECIATION", "POSITIVE", "Thank you for excellent service")
        ('LOW', 'Intent: APPRECIATION, Sentiment: POSITIVE')
        
        >>> compute_priority("GENERAL_ENQUIRY", "NEUTRAL", "What is my policy status?")
        ('MEDIUM', 'Intent: GENERAL_ENQUIRY, Sentiment: NEUTRAL')
    """
    
    # Normalize inputs
    intent = intent.upper() if intent else ""
    sentiment = sentiment.upper() if sentiment else "NEUTRAL"
    
    # Combine summary and body for keyword analysis
    text_to_analyze = f"{summary} {redacted_body}".strip()
    
    # Track decision factors for explanation
    factors = []
    
    # ========================================
    # HIGH PRIORITY RULES
    # ========================================
    
    # Rule 1: COMPLAINT with negative sentiment
    if intent == "COMPLAINT" and sentiment == "NEGATIVE":
        factors.append(f"Intent: {intent}")
        factors.append(f"Sentiment: {sentiment}")
        
        # Check for high-priority keywords
        has_keyword, keyword = _contains_keywords(text_to_analyze, HIGH_PRIORITY_KEYWORDS)
        if has_keyword:
            factors.append(f"Keyword: {keyword}")
        
        explanation = ", ".join(factors)
        return ("HIGH", explanation)
    
    # Rule 2: CLAIM_RELATED with urgency indicators
    if intent == "CLAIM_RELATED":
        has_high_keyword, keyword = _contains_keywords(text_to_analyze, HIGH_PRIORITY_KEYWORDS)
        
        # High priority if negative sentiment OR urgent keywords
        if sentiment == "NEGATIVE" or has_high_keyword:
            factors.append(f"Intent: {intent}")
            if sentiment == "NEGATIVE":
                factors.append(f"Sentiment: {sentiment}")
            if has_high_keyword:
                factors.append(f"Keyword: {keyword}")
            
            explanation = ", ".join(factors)
            return ("HIGH", explanation)
    
    # Rule 3: Any intent with high-priority keywords (especially legal/fraud)
    has_high_keyword, keyword = _contains_keywords(text_to_analyze, HIGH_PRIORITY_KEYWORDS)
    if has_high_keyword and keyword in ["legal", "lawyer", "fraud", "court", "grievance", "escalation", "escalate"]:
        factors.append(f"Critical Keyword: {keyword}")
        if intent:
            factors.append(f"Intent: {intent}")
        
        explanation = ", ".join(factors)
        return ("HIGH", explanation)
    
    # ========================================
    # LOW PRIORITY RULES
    # ========================================
    
    # Rule 4: APPRECIATION emails are low priority
    if intent == "APPRECIATION":
        explanation = f"Intent: {intent}, Sentiment: {sentiment}"
        return ("LOW", explanation)
    
    # Rule 5: Positive sentiment without urgent keywords
    if sentiment == "POSITIVE" and not has_high_keyword:
        factors.append(f"Sentiment: {sentiment}")
        if intent:
            factors.append(f"Intent: {intent}")
        
        explanation = ", ".join(factors)
        return ("LOW", explanation)
    
    # Rule 6: OTHER intent with no urgent indicators
    if intent == "OTHER" and sentiment != "NEGATIVE" and not has_high_keyword:
        explanation = f"Intent: {intent}, Sentiment: {sentiment}"
        return ("LOW", explanation)
    
    # ========================================
    # MEDIUM PRIORITY (DEFAULT)
    # ========================================
    
    # All other cases: GENERAL_ENQUIRY, REQUEST, PAYMENT_ISSUE, POLICY_UPDATE, etc.
    # Without urgent indicators fall into MEDIUM priority
    
    factors = []
    if intent:
        factors.append(f"Intent: {intent}")
    if sentiment:
        factors.append(f"Sentiment: {sentiment}")
    
    # Check if it has medium-priority keywords
    has_medium_keyword, keyword = _contains_keywords(text_to_analyze, MEDIUM_PRIORITY_KEYWORDS)
    if has_medium_keyword:
        factors.append(f"Keyword: {keyword}")
    
    explanation = ", ".join(factors) if factors else "Default classification"
    return ("MEDIUM", explanation)


# Self-test examples (can be run as doctest or manual verification)
if __name__ == "__main__":
    print("Testing Priority Engine...")
    print()
    
    # Test HIGH priority
    print("HIGH Priority Tests:")
    print(compute_priority("COMPLAINT", "NEGATIVE", "My claim has been delayed for 3 months"))
    print(compute_priority("CLAIM_RELATED", "NEGATIVE", "Death claim not processed"))
    print(compute_priority("REQUEST", "NEUTRAL", "I want to file a legal complaint against LIC"))
    print()
    
    # Test MEDIUM priority
    print("MEDIUM Priority Tests:")
    print(compute_priority("GENERAL_ENQUIRY", "NEUTRAL", "What is my policy status?"))
    print(compute_priority("REQUEST", "NEUTRAL", "Please update my address"))
    print(compute_priority("PAYMENT_ISSUE", "NEUTRAL", "Premium payment details needed"))
    print()
    
    # Test LOW priority
    print("LOW Priority Tests:")
    print(compute_priority("APPRECIATION", "POSITIVE", "Thank you for excellent service"))
    print(compute_priority("OTHER", "NEUTRAL", "Just wanted to say hello"))
    print(compute_priority("GENERAL_ENQUIRY", "POSITIVE", "Great to have LIC policy"))
    print()
    
    print("✅ Priority Engine Tests Complete")
