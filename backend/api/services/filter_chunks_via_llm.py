import logging
from typing import List
from backend.api.services.llm_client import call_llm
from backend.prompts import FILTER_SYSTEM_PROMPT, FILTER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def filter_chunks_via_llm(question: str, top_chunks: List[str]) -> List[int]:
    """
    Запрашивает у LLM выбор тех чанков, которые содержат точный текст закона, подходящий под вопрос.
    Возвращает список выбранных индексов (начиная с 1).
    """
    try:
        logger.info("=== Начало фильтрации чанков через LLM ===")
        logger.info(f"Вопрос пользователя: {question}")
        logger.info(f"Получено чанков для фильтрации: {len(top_chunks)}")

        # 1️⃣ Пронумеровываем чанки
        numbered_chunks_lines = []
        for idx, chunk in enumerate(top_chunks, start=1):
            numbered_chunks_lines.append(f"{idx}. {chunk.strip()}")

        numbered_chunks_text = "\n\n".join(numbered_chunks_lines)
        logger.debug(f"Пронумерованные чанки (первые 2000 символов):\n{numbered_chunks_text[:2000]}")

        # 2️⃣ Формируем итоговый промпт с помощью шаблона
        user_prompt = FILTER_USER_PROMPT_TEMPLATE.format(
            question=question,
            chunks=numbered_chunks_text
        )
        full_prompt = f"{FILTER_SYSTEM_PROMPT}\n\n=== QUESTION ===\n{user_prompt}"
        logger.debug(f"Финальный промпт для LLM (первые 2000 символов):\n{full_prompt[:2000]}")

        # 3️⃣ Запрос к LLM
        llm_response = await call_llm(full_prompt)
        logger.info(f"Ответ LLM (сырой): '{llm_response}'")

        # 4️⃣ Парсинг ответа — ожидаем список номеров через запятую
        selected_indices = []
        if llm_response.strip():
            parts = llm_response.strip().split(",")
            for part in parts:
                part = part.strip()
                if part.isdigit():
                    selected_indices.append(int(part))
                else:
                    logger.warning(f"Ненумерованная часть в ответе LLM: '{part}'")

        logger.info(f"Выбранные номера чанков: {selected_indices}")

        return selected_indices

    except Exception as e:
        logger.error(f"Ошибка в filter_chunks_via_llm: {e}", exc_info=True)
        return []
