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
Your goal is to analyze the following email, referencing the provided LIC Policy Context if relevant, and determine the intent, sentiment, and a specific suggested action.

CONTEXT from LIC Policies:
{context}

EMAIL CONTENT (Redacted):
{email}

INSTRUCTIONS:
1. Analyze the email sentiment (Positive, Negative, Neutral).
2. Determine the core intent (e.g., Claim Enquiry, Surrender, Policy Status, Complaint).
3. Based on the Context and Email, suggest a specific, actionable step for the support agent.
4. Output STRICT JSON format.

JSON STRUCTURE:
{{
    "intent": "string",
    "sentiment": "string",
    "suggested_action": "string"
}}
"""

@lru_cache(maxsize=1)
def get_chain():
    """Builds and caches the RAG chain."""
    logger.info("Initializing LLM Chain (gemma2:2b)...")
    llm = ChatOllama(model="gemma2:2b", format="json", temperature=0)
    
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
            "intent": "Unknown",
            "sentiment": "Neutral",
            "suggested_action": "Review Empty Email"
        }
        
    try:
        chain = get_chain()
        logger.info("Invoking RAG Chain...")
        result = chain.invoke(redacted_body)
        logger.info("Analysis complete.")
        return result
    except Exception as e:
        logger.error(f"RAG Chain failed: {e}")
        # Return fallback structure
        return {
            "intent": "Unknown",
            "sentiment": "Neutral",
            "suggested_action": "Manual Review Required (AI Error)"
        }
