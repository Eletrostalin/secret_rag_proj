import logging
from typing import List

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.db.models import Base, Chunk
from backend.db.schemas import ChunkData

# Логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Подключение к БД
DATABASE_URL = "postgresql+asyncpg://nickstanchenkov:010125hipaa@localhost:5432/rag_hipaa"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Кастомное исключение
class DatabaseError(Exception):
    pass


# Создание таблиц
async def init_db():
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized.")
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
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