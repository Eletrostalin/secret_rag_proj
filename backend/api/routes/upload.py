import logging
import tempfile
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from backend.ingestion.ingest_service import ingest_pdf_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.post("/", tags=["Upload"])
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"Получен файл: {file.filename}")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(f"Временный файл сохранён: {tmp_path}")

        # Запускаем ingestion
        chunk_count = await ingest_pdf_file(tmp_path)
        logger.info(f"Ingestion завершён. Всего чанков: {chunk_count}")

        return JSONResponse(content={"status": "success", "chunks": chunk_count})

    except Exception as e:
        logger.error(f"Ошибка при обработке PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))