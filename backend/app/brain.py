import logging
import json
from functools import lru_cache
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.rag import get_retriever

# Setup Logging
logger = logging.getLogger("Brain")

# Define Prompt Template
TEMPLATE = """
You are an expert Email Intelligence Agent for LIC (Life Insurance Corporation of India).

You analyze customer emails for internal support use.
Your output MUST be accurate, conservative, and deterministic.

IMPORTANT ARCHITECTURAL RULE:
- Retrieval-Augmented Generation (RAG) is provided ONLY as background knowledge.
- RAG MUST NOT influence intent classification unless the email explicitly mentions it.
- Classification rules MUST be followed strictly.

---

INTENT CLASSIFICATION (CLOSED SET — CHOOSE ONE ONLY):

- REQUEST
- COMPLAINT
- GENERAL_ENQUIRY
- CLAIM_RELATED
- PAYMENT_ISSUE
- POLICY_UPDATE
- APPRECIATION
- OTHER

---

STRICT DECISION RULES (MANDATORY):

1. CLAIM_RELATED:
   - Choose this ONLY IF the email explicitly mentions:
     - the word "claim"
     - a claim number
     - claim submission
     - claim settlement
   - Do NOT infer claims from policy context or RAG documents.

2. APPRECIATION:
   - Choose this if the email expresses thanks, praise, or positive feedback.
   - Do NOT combine with other intents.

3. COMPLAINT:
   - Choose this if the email expresses dissatisfaction, delay, or frustration.

4. REQUEST:
   - Choose this if the user is asking for an action, process, or assistance.

5. GENERAL_ENQUIRY:
   - Choose this if the email is informational or unclear.
   - This is the DEFAULT fallback if no other category applies.

6. PAYMENT_ISSUE:
   - Choose this ONLY for premium, maturity, refund, or payment-related issues.

7. POLICY_UPDATE:
   - Choose this ONLY for address, nominee, or contact detail changes.

8. OTHER:
   - Use this ONLY if nothing else applies.

NEVER leave intent empty.
NEVER guess.
If unsure → use GENERAL_ENQUIRY.

---

SENTIMENT ANALYSIS RULES:
- POSITIVE: Expresses gratitude, satisfaction, or happiness.
- NEGATIVE: Expresses frustration, anger, disappointment, or urgency.
- NEUTRAL: Factual, politely inquiring, or strictly informational.

---

SUMMARY GENERATION RULES:

- Generate a concise, professional summary in 1–2 sentences.
- Capture the core issue or request.
- Do NOT include any PII.
- Do NOT add recommendations or actions.

---

EMAIL CONTENT (PII REDACTED):
{email}

OPTIONAL CONTEXT (FOR UNDERSTANDING ONLY — NOT FOR CLASSIFICATION):
{context}

---

OUTPUT FORMAT (STRICT JSON ONLY):

{{
  "intent": "REQUEST | COMPLAINT | GENERAL_ENQUIRY | CLAIM_RELATED | PAYMENT_ISSUE | POLICY_UPDATE | APPRECIATION | OTHER",
  "sentiment": "POSITIVE | NEGATIVE | NEUTRAL",
  "summary": "string",
  "confidence": "High | Medium | Low"
}}

---

FINAL CHECK (MANDATORY SELF-VERIFICATION):

Before responding, internally verify:
- Did I choose CLAIM_RELATED ONLY if explicitly mentioned in the email?
- Did I avoid letting RAG influence the intent?
- Is the summary neutral and accurate?
- Did I include sentiment?

If any answer is NO, fix it before responding.
"""

@lru_cache(maxsize=1)
def get_chain():
    """Builds and caches the RAG chain."""
    logger.info("Initializing LLM Chain (llama3)...")
    llm = ChatOllama(model="llama3", format="json", temperature=0, timeout=30.0)
    
    prompt = PromptTemplate(
        input_variables=["context", "email"],
        template=TEMPLATE
    )
    
    retriever = get_retriever()
    
    chain = (
        {"context": retriever, "email": RunnablePassthrough()}
        | prompt
        | llm
        | JsonOutputParser()
    )
    return chain

def analyze_email(redacted_body: str) -> dict:
    if not redacted_body:
        return {
            "intent": "GENERAL_ENQUIRY",
            "sentiment": "NEUTRAL",
            "summary": "Empty email body.",
            "confidence": "Low"
        }
        
    try:
        chain = get_chain()
        logger.info("Invoking RAG Chain...")
        result = chain.invoke(redacted_body)
        logger.info("Analysis complete.")
        return result
    except Exception as e:
        logger.error(f"RAG Chain failed: {e}")
        logger.warning("Using fallback analysis (LLM unavailable)")
        # Return fallback with indication that LLM service is unavailable
        return {
            "intent": "GENERAL_ENQUIRY",
            "sentiment": "NEUTRAL",
            "summary": f"LLM Service Unavailable. Email received and queued for review.",
            "confidence": "Low"
        }
