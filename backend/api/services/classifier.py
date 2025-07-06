import logging
from backend.api.services.llm_client import call_llm
from backend.prompts import CLASSIFICATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def classify_request(question: str) -> str:
    """
    Классифицирует запрос как NORMAL или QUOTE.
    """
    prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\nUser: \"{question}\"\nAnswer:"
    logger.info(f"Classifying question: {question}")

    try:
        classification = await call_llm(prompt)
        classification = classification.strip().upper()

        if classification not in ["NORMAL", "QUOTE"]:
            logger.warning(f"Unexpected classification response: {classification}. Defaulting to NORMAL.")
            return "NORMAL"

        logger.info(f"Classification result: {classification}")
        return classification

    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return "NORMAL"