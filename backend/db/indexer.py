import logging
from sqlalchemy import update, func
from sqlalchemy.exc import SQLAlchemyError
from backend.db.models import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class IndexingError(Exception):
    """Кастомное исключение для ошибок индексации"""
    pass

async def add_bm25_index(session):
    """
    Проставляет значение bm25_text через PostgreSQL to_tsvector
    для всех Chunk без уже проставленного bm25_text.
    """
    logger.info("Начинаем индексацию BM25 через to_tsvector")

    try:
        async with session.begin():
            result = await session.execute(
                update(Chunk)
                .where(Chunk.bm25_text == None)
                .values(bm25_text=func.to_tsvector('english', Chunk.text))
            )

        logger.info(f"✅ BM25 индексация завершена. Обновлено строк: {result.rowcount}")

    except SQLAlchemyError as e:
        logger.error(f"Ошибка при индексации BM25: {e}")
        raise IndexingError("Не удалось выполнить индексацию BM25")