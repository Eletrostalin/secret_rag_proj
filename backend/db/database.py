import logging
import asyncio
from typing import List, Callable, Any

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from backend.config import DATABASE_URL
from backend.db.models import Base, Chunk
from backend.db.schemas import ChunkData

# Логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Кастомное исключение
class DatabaseError(Exception):
    pass


# Универсальный помощник с ретраями
async def with_retries(
    func: Callable,
    *args,
    max_retries: int = 3,
    delay: float = 2.0,
    **kwargs
) -> Any:
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt} for {func.__name__}")
            return await func(*args, **kwargs)
        except (OperationalError, SQLAlchemyError) as e:
            last_exception = e
            logger.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
    logger.error(f"All {max_retries} attempts failed for {func.__name__}")
    raise DatabaseError(f"Failed after {max_retries} attempts") from last_exception


# Создание таблиц
async def init_db():
    logger.info("🟢 [init_db] Called: Starting database initialization process...")
    try:
        async with engine.begin() as conn:
            logger.info("🟡 [init_db] Acquired connection. Running Base.metadata.create_all()...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("🟢 [init_db] Base.metadata.create_all() completed. Tables are ensured to exist.")
        logger.info("✅ [init_db] Database initialization process finished successfully.")
    except SQLAlchemyError as e:
        logger.error(f"❌ [init_db] Error during database initialization: {e}")
        raise DatabaseError("Failed to initialize database.")


# Dependency для FastAPI
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


# Сохранение чанков
async def save_chunks(chunks: List[ChunkData]):
    logger.info(f"Saving {len(chunks)} chunks to DB...")
    try:
        async with async_session() as session:
            async with session.begin():
                for chunk in chunks:
                    db_chunk = Chunk(
                        part_number=chunk.part_number,
                        #subpart=chunk.subpart,
                        section_number=chunk.section_number,
                        text=chunk.text,
                        meta={"cross_references": chunk.cross_references},
                        parent_id=None,
                        parent_section_number=None,
                        title=None,
                        bm25_text=None,
                        embedding_vector=None
                    )
                    session.add(db_chunk)
        logger.info("✅ All chunks saved successfully.")
    except SQLAlchemyError as e:
        logger.error(f"Error saving chunks: {e}")
        raise DatabaseError("Failed to save chunks.")


# Получение чанков без эмбеддингов
async def get_chunks_without_embeddings(session) -> List[Chunk]:
    logger.info("Fetching chunks without embeddings...")
    try:
        result = await session.execute(
            select(Chunk).where(Chunk.embedding_vector == None)
        )
        chunks = result.scalars().all()
        logger.info(f"Found {len(chunks)} chunks without embeddings.")
        return chunks
    except SQLAlchemyError as e:
        logger.error(f"Error fetching chunks: {e}")
        raise DatabaseError("Failed to fetch chunks.")


# Сохранение эмбеддингов
async def save_embeddings(session, chunks_with_vectors):
    logger.info(f"Saving embeddings for {len(chunks_with_vectors)} chunks...")
    try:
        for chunk, embedding in chunks_with_vectors:
            chunk.embedding_vector = embedding
        await session.commit()
        logger.info("✅ Embeddings saved successfully.")
    except SQLAlchemyError as e:
        logger.error(f"Error saving embeddings: {e}")
        await session.rollback()
        raise DatabaseError("Failed to save embeddings.")