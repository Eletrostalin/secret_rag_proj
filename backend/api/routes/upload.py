import logging
import os
import uuid
import tempfile
import shutil
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.ingestion.ingest_service import ingest_pdf_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Хранилище задач
tasks = {}

@router.post("/", tags=["Upload"])
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"📥 Получен файл: {file.filename}")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    tmp_path = None
    task_id = str(uuid.uuid4())

    try:
        # Сохраняем файл во временное место
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(f"✅ Временный файл сохранён: {tmp_path}")

        # ✅ Регистрируем задачу как PENDING
        tasks[task_id] = {"status": "PENDING", "result": None, "error": None}

        async def ingestion_task():
            try:
                logger.info(f"🚀 Ingestion task started for {task_id}")
                chunk_count = await ingest_pdf_file(tmp_path)
                tasks[task_id]["status"] = "DONE"
                tasks[task_id]["result"] = {"chunks": chunk_count}
                logger.info(f"🎯 Ingestion task complete for {task_id}, chunks={chunk_count}")

            except Exception as e:
                logger.error(f"❌ Error in ingestion task for {task_id}: {e}")
                tasks[task_id]["status"] = "ERROR"
                tasks[task_id]["error"] = str(e)

            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                        logger.info(f"🧹 Временный файл удалён: {tmp_path}")
                    except Exception as remove_err:
                        logger.warning(f"⚠️ Не удалось удалить временный файл: {tmp_path}. Ошибка: {remove_err}")

        # ✅ Запускаем ingestion в фоне
        asyncio.create_task(ingestion_task())

        # Сразу отвечаем пользователю task_id
        return JSONResponse(content={"status": "started", "task_id": task_id})

    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", tags=["Upload"])
async def get_upload_status(task_id: str = Query(..., description="ID задачи для проверки статуса")):
    """
    Проверяет статус задачи загрузки по task_id.
    """
    task_info = tasks.get(task_id)
    if not task_info:
        logger.warning(f"Запрос статуса для неизвестного task_id: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found.")

    return JSONResponse(content={"task_id": task_id, **task_info})