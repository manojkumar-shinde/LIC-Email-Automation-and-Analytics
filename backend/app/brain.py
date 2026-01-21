import logging
import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.rag import get_retriever

# Setup Logging
logger = logging.getLogger("Brain")

# Initialize LLM
llm = ChatOllama(model="gemma2:2b", format="json")

# Define Prompt
template = """
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

prompt = PromptTemplate(
    input_variables=["context", "email"],
    template=template
)

# Chain
def analyze_email(redacted_body: str) -> dict:
    retriever = get_retriever()
    
    chain = (
        {"context": retriever, "email": RunnablePassthrough()}
        | prompt
        | llm
        | JsonOutputParser()
    )
    
    try:
        logger.info("Invoking RAG Chain...")
        result = chain.invoke(redacted_body)
        logger.info("Analysis complete.")
        return result
    except Exception as e:
        logger.error(f"RAG Chain failed: {e}")
        return {
            "intent": "Unknown",
            "sentiment": "Neutral",
            "suggested_action": "Manual Review Required (AI Error)"
        }
