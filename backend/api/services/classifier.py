import logging
import re

from backend.api.services.llm_client import call_llm
from backend.prompts import CLASSIFICATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def classify_request(question: str) -> dict:
    """
    Классифицирует запрос как NORMAL или QUOTE.
    Также извлекает номер параграфа, если он явно указан в запросе (например, QUOTE 164.104).

    Возвращает:
        {
            "mode": "NORMAL" | "QUOTE",
            "target_section": Optional[str]
        }
    """
    prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\nUser: \"{question}\"\nAnswer:"
    logger.info(f"Classifying question: {question}")

    try:
        classification = await call_llm(prompt)
        classification = classification.strip().upper()
        logger.info(f"Raw classification response: {classification}")

        # Пример: "QUOTE 164.104"
        match = re.match(r"QUOTE\s+(\d{3}\.\d{3})", classification)
        if match:
            section = match.group(1)
            return {"mode": "QUOTE", "target_section": section}

        if classification in {"NORMAL", "QUOTE"}:
            return {"mode": classification, "target_section": None}

        logger.warning(f"Unexpected classification: {classification}. Defaulting to NORMAL.")
        return {"mode": "NORMAL", "target_section": None}

    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return {"mode": "NORMAL", "target_section": None}