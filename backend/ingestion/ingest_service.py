import asyncio
import logging
from backend.ingestion.parser import parse_pdf
from backend.ingestion.chunker import chunk_texts_to_chunks
from backend.db.database import async_session, get_chunks_without_embeddings, save_embeddings, with_retries
from backend.db.indexer import add_bm25_index
from backend.ingestion.embedder import embed_batch
from backend.db.database import save_chunks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def ingest_pdf_file(pdf_path: str) -> int:
    """
    Главный пайплайн: парсинг PDF -> чанкование -> запись в БД -> эмбеддинги -> BM25 индексация.
    Возвращает количество записанных чанков.
    """
    logger.info("========== Ingestion pipeline started ==========")
    logger.info(f"📥 Input PDF path: {pdf_path}")

    # Шаг 1: Парсинг PDF
    try:
        logger.info("🚀 Step 1: Parsing PDF...")
        pages = await parse_pdf(pdf_path, pdf_path)
        if not pages:
            raise ValueError("PDF парсинг вернул пустой результат.")
        logger.info(f"✅ Parsing complete. Total pages: {len(pages)}")
        for i, page in enumerate(pages, 1):
            logger.debug(f"Page {i}: {page[:200]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка на этапе парсинга PDF: {e}")
        raise

    # Шаг 2: Чанкование
    try:
        logger.info("🚀 Step 2: Chunking pages...")
        chunks = chunk_texts_to_chunks(pages)
        if not chunks:
            raise ValueError("Чанкование вернуло пустой список.")
        logger.info(f"✅ Chunking complete. Total chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            logger.debug(f"Chunk {i}: {chunk.section_number} | {chunk.text[:200]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка на этапе чанкования: {e}")
        raise

    # Шаг 3: Сохранение чанков в БД
    try:
        logger.info("🚀 Step 3: Saving chunks to DB with retries...")
        await with_retries(save_chunks, chunks)
        logger.info(f"✅ {len(chunks)} chunks successfully saved to DB.")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении чанков в БД: {e}")
        raise

    # Шаг 4: Генерация и сохранение эмбеддингов
    try:
        logger.info("🚀 Step 4: Generating and saving embeddings...")
        async with async_session() as session:
            chunks_to_embed = await with_retries(get_chunks_without_embeddings, session)
            logger.info(f"Chunks needing embeddings: {len(chunks_to_embed)}")

            if chunks_to_embed:
                texts = [chunk.text for chunk in chunks_to_embed]
                logger.debug(f"Texts for embedding (first 2): {[t[:100] for t in texts[:2]]}")
                vectors = await asyncio.to_thread(embed_batch, texts)
                logger.debug(f"Generated embeddings: {vectors[:2]}")

                chunks_with_vectors = list(zip(chunks_to_embed, vectors))
                await with_retries(save_embeddings, session, chunks_with_vectors)
                logger.info(f"✅ Embeddings added for {len(chunks_with_vectors)} chunks.")
            else:
                logger.info("✅ No chunks needed embeddings.")
    except Exception as e:
        logger.error(f"❌ Ошибка на этапе генерации эмбеддингов: {e}")
        raise

    # Шаг 5: Индексация BM25
    try:
        logger.info("🚀 Step 5: Creating BM25 index with retries...")
        async with async_session() as session:
            await with_retries(add_bm25_index, session)
            logger.info("✅ BM25 indexing complete.")
    except Exception as e:
        logger.error(f"❌ Ошибка на этапе индексации BM25: {e}")
        raise

    logger.info(f"🎯 Ingestion completed successfully. Total new chunks: {len(chunks)}")
    logger.info("========== Ingestion pipeline finished ==========")
    return len(chunks)