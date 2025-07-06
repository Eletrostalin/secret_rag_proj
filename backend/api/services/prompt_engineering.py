import logging
from backend.prompts import ANSWER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_prompt(question: str, context: str) -> str:
    """
    Формирует промпт для LLM.
    Склеивает инструкцию, контекст и вопрос.
    Использует централизованный ANSWER_SYSTEM_PROMPT.
    """
    logger.info("Генерация промпта для LLM")

    prompt = ANSWER_SYSTEM_PROMPT.format(
        context=context.strip(),
        question=question.strip()
    )

    logger.info(f"Полный сформированный промпт (длина {len(prompt)} символов):\n{prompt}")
    return prompt