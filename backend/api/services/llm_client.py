import logging
import asyncio
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Инициализация асинхронного клиента OpenAI один раз на модуль
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Таймаут на случай, если модель зависнет
DEFAULT_LLM_TIMEOUT = 60


def try_split_prompt(prompt: str):
    """
    Проверяет, есть ли в prompt специальный маркер === QUESTION ===.
    Если есть — разбивает prompt на две части:
      - system_content
      - user_content
    Это позволяет использовать кастомные system-подсказки.

    Если маркера нет, возвращает None — значит будет fallback на дефолтный system prompt.
    """
    if "=== QUESTION ===" in prompt:
        parts = prompt.split("=== QUESTION ===")
        system_part = parts[0].strip()
        user_part = parts[1].strip()
        logger.debug("Detected structured prompt with marker.")
        return system_part, user_part

    return None


async def call_llm(prompt: str, model: str = None) -> str:
    """
    Универсальная точка входа для запроса к LLM.
    - Разбирает prompt на system/user части (если есть маркер === QUESTION ===)
    - Если маркера нет — использует дефолтный system prompt
    - Делает асинхронный вызов к OpenAI ChatCompletion
    - Оборачивает вызов в timeout
    - Логирует результат и возвращает текст

    Этот метод позволяет гибко отправлять и простые, и форматированные промпты.
    """
    chosen_model = model or OPENAI_MODEL
    logger.info(f"Calling OpenAI model: {chosen_model}")

    # --- 1️⃣ Разбор prompt на system/user роли
    split_result = try_split_prompt(prompt)
    if split_result:
        system_content, user_content = split_result
    else:
        # Фоллбек, если маркера нет
        system_content = "You are a helpful assistant."
        user_content = prompt.strip()

    logger.debug(f"SYSTEM MESSAGE (truncated): {system_content[:500]}")
    logger.debug(f"USER MESSAGE (truncated): {user_content[:500]}")

    # --- 2️⃣ Внутренняя корутина для OpenAI вызова
    async def _call_openai():
        """
        Фактический вызов к OpenAI API.
        Вынесено в подфункцию для удобного оборачивания в timeout.
        """
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()

    # --- 3️⃣ Защита таймаутом
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