import logging
import sys
import asyncio

from backend.db.indexer import add_bm25_index
from backend.ingestion.embedder import embed_batch
from backend.ingestion.parser import parse_pdf
from backend.ingestion.chunker import chunk_texts_to_chunks
from backend.db.database import save_chunks, get_chunks_without_embeddings, async_session, save_embeddings

logging.basicConfig(level=logging.INFO)


async def main():
    if len(sys.argv) < 3:
        print("Usage: python -m backend.scripts.cli_parse_and_chunk_plain <input.pdf> <working.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    working_pdf = sys.argv[2]

    # Шаг 1
    pages = await parse_pdf(input_pdf, working_pdf)
    if pages is None:
        logging.error("Парсер вернул None.")
        raise ValueError("Parsing failed: no pages returned.")

    logging.info(f"Получено страниц: {len(pages)}")

    # Шаг 2
    chunks = chunk_texts_to_chunks(pages)
    logging.info(f"Получено чанков: {len(chunks)}")

    for i, chunk in enumerate(chunks, start=1):
        logging.info(f"Чанк {i}:\n{chunk.model_dump_json(indent=2)}")

    # Шаг 3
    await save_chunks(chunks)
    logging.info("✅ Все чанки успешно сохранены в БД.")

    # Шаг 4: эмбеддинги
    async with async_session() as session:
        chunks_to_embed = await get_chunks_without_embeddings(session)

        if chunks_to_embed:
            texts = [chunk.text for chunk in chunks_to_embed]
            vectors = embed_batch(texts)
            chunks_with_vectors = list(zip(chunks_to_embed, vectors))
            await save_embeddings(session, chunks_with_vectors)

            logging.info(f"✅ Добавлены эмбеддинги для {len(chunks_with_vectors)} чанков.")
        else:
            logging.info("✅ Нет чанков без эмбеддингов.")

     # Шаг 5: BM25 индексация
    await add_bm25_index(session)
    logging.info("✅ Индексация BM25 завершена.")


if __name__ == "__main__":
    asyncio.run(main())