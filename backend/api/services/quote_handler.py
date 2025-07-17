import logging
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.services.llm_client import call_llm
from backend.api.services.filter_chunks_via_llm import filter_chunks_via_llm
from backend.db.database import async_session
from backend.db.models import Chunk
from backend.api.services.retrieval import retrieve_top_chunks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def handle_quote_request(question: str, section_number: Optional[str] = None) -> str:
    """
    Обработка запроса типа QUOTE.
    Если section_number передан — ищем конкретный параграф по номеру.
    Если нет — выполняем обычную фильтрацию чанков через LLM.
    """

    async with async_session() as session:
        if section_number:
            formatted_section = f"§ {section_number}"
            logger.info(f"🔍 Ищем параграф по номеру: {formatted_section}")

            stmt = select(Chunk).where(Chunk.section_number == formatted_section)
            result = await session.execute(stmt)
            chunk = result.scalar_one_or_none()

            if chunk:
                return f" {chunk.section_number} ({chunk.part_number})\n{chunk.text.strip()}"
            else:
                logger.warning(f"❌ Не найден параграф с номером {formatted_section}")
                return f"Section §{section_number} was not found in the regulation text."

        # Если номер параграфа не указан — запускаем обычный retrieval + фильтрацию
        logger.info("🔄 Section number не найден. Запускаем retrieval + filter_chunks_via_llm")

        top_chunks: List[Chunk] = await retrieve_top_chunks(question)

        if not top_chunks:
            return "No relevant legal text found."

        selected_indices = await filter_chunks_via_llm(
            question=question,
            top_chunks=[c.text for c in top_chunks]
        )

        if not selected_indices:
            return "No direct legal text found matching your request."

        selected_chunks = [top_chunks[i - 1] for i in selected_indices if 0 < i <= len(top_chunks)]

        return "\n\n".join(
            f"§ {c.section_number} ({c.part_number})\n{c.text.strip()}" for c in selected_chunks
        )