import logging
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def call_llm(prompt: str, model: str = None) -> str:
    """
    Делает асинхронный вызов к LLM и возвращает сгенерированный текст.
    """
    chosen_model = model or OPENAI_MODEL
    logger.info(f"Calling OpenAI model: {chosen_model}")

    try:
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        answer = response.choices[0].message.content.strip()
        logger.info("LLM returned a response")
        return answer

    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        raise