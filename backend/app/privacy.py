import logging
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Setup Logging
logger = logging.getLogger("Privacy")

class RedactionError(Exception):
    """Raised when PII redaction fails."""
    pass

class PIIRedactor:
    def __init__(self):
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            # Entities to redact
            self.entities = ["PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "CREDIT_CARD", "US_SSN", "IP_ADDRESS"]
        except Exception as e:
            logger.critical(f"Failed to initialize Presidio engines: {e}")
            raise e
        
    def redact(self, text: str) -> str:
        if not text:
            return ""
            
        try:
            # Analyze text for PII
            results = self.analyzer.analyze(text=text, entities=self.entities, language='en')
            
            # Redact identified PII
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})
                }
            )
            
            return anonymized_result.text
        except Exception as e:
            logger.error(f"Redaction failed: {e}")
            # FAIL CLOSED: Do NOT return the original text if redaction fails.
            # This prevents accidental leakage of PII/PHI.
            raise RedactionError(f"Privacy processing failed: {e}")

# Singleton instance
try:
    redactor = PIIRedactor()
except Exception:
    logger.critical("Privacy module failed to start.")
    redactor = None

def redact_pii(text: str) -> str:
    if redactor is None:
         raise RedactionError("Redactor service is unavailable.")
    return redactor.redact(text)
