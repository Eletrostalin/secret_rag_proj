import logging
import asyncio
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DEFAULT_LLM_TIMEOUT = 60


def try_split_prompt(prompt: str):
    """
    Делит prompt на system / user, если есть маркер === QUESTION ===.
    Иначе возвращает None.
    """
    if "=== QUESTION ===" in prompt:
        parts = prompt.split("=== QUESTION ===")
        system_part = parts[0].strip()
        user_part = parts[1].strip()
        logger.debug(f"Detected structured prompt with marker.")
        return system_part, user_part
    return None


async def call_llm(prompt: str, model: str = None) -> str:
    """
    Делает асинхронный вызов к LLM и возвращает сгенерированный текст.
    Универсально работает с любым prompt.
    """
    chosen_model = model or OPENAI_MODEL
    logger.info(f"Calling OpenAI model: {chosen_model}")

    split_result = try_split_prompt(prompt)
    if split_result:
        system_content, user_content = split_result
    else:
        # Однолинейный режим (для query rewriting / expansion)
        system_content = "You are a helpful assistant."
        user_content = prompt.strip()

    logger.debug(f"SYSTEM MESSAGE: {system_content[:500]}")
    logger.debug(f"USER MESSAGE: {user_content[:500]}")

    async def _call_openai():
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2
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