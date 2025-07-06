import logging
from backend.prompts import ANSWER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_prompt(question: str, context: str) -> str:
    """
    Формирует промпт для LLM.
    Логирует все ключевые части для дебага.
    """
    logger.info("=== Генерация PROMPT для LLM ===")
    logger.info(f"QUESTION:\n{question.strip()}")

    if not context.strip():
        logger.warning("⚠️ CONTEXT пустой!")
    else:
        # Ограничим вывод в логах, чтобы не раздувать
        preview_length = 1000
        context_preview = context.strip()[:preview_length]
        logger.info(f"CONTEXT (первые {preview_length} символов):\n{context_preview}")

    prompt = ANSWER_SYSTEM_PROMPT.format(
        context=context.strip(),
        question=question.strip()
    )

    prompt_preview_length = 2000
    prompt_preview = prompt[:prompt_preview_length]
    logger.info(f"FINAL PROMPT (первые {prompt_preview_length} символов):\n{prompt_preview}")
    logger.debug(f"Полная длина PROMPT: {len(prompt)} символов")

    return prompt