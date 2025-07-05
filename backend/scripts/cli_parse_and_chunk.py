import logging
import sys
import asyncio

from backend.ingestion.parser import parse_pdf
from backend.ingestion.chunker import chunk_texts_to_chunks
from backend.db.database import save_chunks

logging.basicConfig(level=logging.INFO)


async def main():
    if len(sys.argv) < 3:
        print("Usage: python -m backend.scripts.cli_parse_and_chunk_plain <input.pdf> <working.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    working_pdf = sys.argv[2]

    # Шаг 1: парсим PDF → получаем страницы без титулов
    pages = parse_pdf(input_pdf, working_pdf)
    if pages is None:
        logging.error("Парсер вернул None. Проверь функцию parse_pdf, чтобы она возвращала список.")
        raise ValueError("Parsing failed: no pages returned.")

    logging.info(f"Получено страниц: {len(pages)}")

    # Шаг 2: чанкование страниц
    chunks = chunk_texts_to_chunks(pages)
    logging.info(f"Получено чанков: {len(chunks)}")

    for i, chunk in enumerate(chunks, start=1):
        logging.info(f"Чанк {i}:\n{chunk.model_dump_json(indent=2)}")

    # Шаг 3: сохраняем чанки в БД
    await save_chunks(chunks)
    logging.info("✅ Все чанки успешно сохранены в БД.")


if __name__ == "__main__":
    asyncio.run(main())