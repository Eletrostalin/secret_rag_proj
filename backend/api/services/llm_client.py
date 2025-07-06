import logging
import asyncio
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL
from backend.prompts import MAIN_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Настраиваемый таймаут запроса к модели (в секундах)
DEFAULT_LLM_TIMEOUT = 30


async def call_llm(prompt: str, model: str = None) -> str:
    """
    Делает асинхронный вызов к LLM и возвращает сгенерированный текст.
    Использует централизованный system prompt.
    """
    chosen_model = model or OPENAI_MODEL
    logger.info(f"Calling OpenAI model: {chosen_model}")

    async def _call_openai():
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": MAIN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
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