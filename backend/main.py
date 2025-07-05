import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем только нужные роуты
from backend.api.routes import ask
# from backend.api.routes import section  # Убрали, чтобы не падало при импорте

from backend.ingestion.chunker import chunk_texts_to_chunks
from backend.ingestion.parser import parse_pdf

app = FastAPI(
    title="HIPAA RAG API",
    description="Retrieval-Augmented Generation service for HIPAA queries",
    version="0.1.0"
)

# CORS Middleware — разрешаем фронтенду общаться с бекендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Можно ограничить на проде
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(ask.router, prefix="/ask", tags=["Ask"])
# app.include_router(section.router, prefix="/section", tags=["Section"])  # Убрали

# Healthcheck endpoint
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


# Позволяет вызвать инициализацию БД вручную
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <input.pdf> <working.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    working_pdf = sys.argv[2]

    # Шаг 1: парсим PDF и получаем текст страниц
    pages = parse_pdf(input_pdf, working_pdf)
    logging.info(f"Получено страниц: {len(pages)}")

    # Шаг 2: чанкование страниц
    chunks = chunk_texts_to_chunks(pages)
    logging.info(f"Получено чанков: {len(chunks)}")

    # Шаг 3: вывод всех чанков в лог
    for i, chunk in enumerate(chunks, start=1):
        logging.info(f"Чанк {i}:\n{chunk.model_dump_json(indent=2)}")