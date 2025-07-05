from typing import List

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from backend.db.models import Base, Chunk
from backend.db.schemas import ChunkData

# Подключение к БД
DATABASE_URL = "postgresql+asyncpg://nickstanchenkov:010125hipaa@localhost:5432/rag_hipaa"

engine = create_async_engine(DATABASE_URL, echo=False)

# Сессии
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Dependency для FastAPI
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def save_chunks(chunks: List[ChunkData]):
    async with async_session() as session:
        async with session.begin():
            for chunk in chunks:
                db_chunk = Chunk(
                    part_number=chunk.part_number,
                    #subpart=chunk.subpart,
                    section_number=chunk.section_number,
                    text=chunk.text,
                    meta={
                        "cross_references": chunk.cross_references
                    },
                    parent_id=None,
                    parent_section_number=None,
                    title=None,
                    bm25_text=None,
                    embedding_vector=None
                )
                session.add(db_chunk)


async def get_chunks_without_embeddings(session) -> List[Chunk]:
    result = await session.execute(
        select(Chunk).where(Chunk.embedding_vector == None)
    )
    return result.scalars().all()


async def save_embeddings(session, chunks_with_vectors):
    for chunk, embedding in chunks_with_vectors:
        chunk.embedding_vector = embedding
    await session.commit()