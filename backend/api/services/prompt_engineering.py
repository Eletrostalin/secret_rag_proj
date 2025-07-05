import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SYSTEM_PROMPT = """
You are a HIPAA compliance expert.
Answer the question strictly and only using the CONTEXT below.
If the answer is not present in the context, say you do not know and do not invent anything.
Cite the relevant sections by their § number when available.

CONTEXT:
{context}

QUESTION:
{question}
"""

def generate_prompt(question: str, context: str) -> str:
    """
    Формирует промпт для LLM.
    Склеивает системную инструкцию, контекст и вопрос.
    """
    logger.info("Генерация промпта для LLM")

    prompt = SYSTEM_PROMPT.format(context=context.strip(), question=question.strip())

    logger.debug(f"Сформированный промпт (длина {len(prompt)} символов)")
    return prompt