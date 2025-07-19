import logging
import asyncio
from typing import Optional, Literal
from openai import AsyncOpenAI

from backend.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL_ANSWER,
    OPENAI_MODEL_CLASSIFY,
    OPENAI_MODEL_REWRITE,
    OPENAI_MODEL_EXPAND,
    OPENAI_MODEL_FILTER,
    OPENAI_MODEL_RERANK,
)

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Таймаут на случай, если модель зависнет
DEFAULT_LLM_TIMEOUT = 60


def select_model(purpose: Optional[Literal["classification", "rewrite", "expand", "filter", "rerank", "answer"]]) -> str:
    """
    Возвращает модель в зависимости от цели вызова.
    """
    return {
        "classification": OPENAI_MODEL_CLASSIFY,
        "rewrite": OPENAI_MODEL_REWRITE,
        "expand": OPENAI_MODEL_EXPAND,
        "filter": OPENAI_MODEL_FILTER,
        "rerank": OPENAI_MODEL_RERANK,
        "answer": OPENAI_MODEL_ANSWER,
    }.get(purpose, OPENAI_MODEL_ANSWER)  # fallback на "answer"


def try_split_prompt(prompt: str):
    """
    Проверяет, есть ли в prompt специальный маркер === QUESTION ===.
    Если есть — разбивает prompt на две части:
      - system_content
      - user_content
    """
    if "=== QUESTION ===" in prompt:
        parts = prompt.split("=== QUESTION ===")
        system_part = parts[0].strip()
        user_part = parts[1].strip()
        logger.debug("Detected structured prompt with marker.")
        return system_part, user_part

    return None


async def call_llm(prompt: str, purpose: Optional[str] = None, model: Optional[str] = None) -> str:
    """
    Универсальная точка входа для запроса к LLM.
    - Поддерживает выбор модели через `purpose` или явный `model`.
    - Поддерживает кастомные system/user части через "=== QUESTION ===".
    - Оборачивает вызов в timeout.
    """
    chosen_model = model or select_model(purpose)
    logger.info(f"Calling OpenAI model: {chosen_model}")

    # --- Разбор system/user prompt
    split_result = try_split_prompt(prompt)
    if split_result:
        system_content, user_content = split_result
    else:
        system_content = "You are a helpful assistant."
        user_content = prompt.strip()

    logger.debug(f"SYSTEM MESSAGE (truncated): {system_content[:500]}")
    logger.debug(f"USER MESSAGE (truncated): {user_content[:500]}")

    async def _call_openai():
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()

    try:
        answer = await asyncio.wait_for(_call_openai(), timeout=DEFAULT_LLM_TIMEOUT)
        logger.info("LLM returned a response")
        return answer

    except asyncio.TimeoutError:
        logger.error(f"Timeout calling LLM after {DEFAULT_LLM_TIMEOUT}s")
        raise Exception("Timeout contacting the language model. Please try again later.")

    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        raise Exception("Error communicating with the language model.")


# def select_model(purpose: Optional[str]) -> str:
#     """
#     ВРЕМЕННАЯ ЗАГЛУШКА:
#     Всегда возвращает модель для финального ответа — OPENAI_MODEL_ANSWER,
#     независимо от цели запроса (classification, rewrite и т.д.).
#     """
#     return OPENAI_MODEL_ANSWER