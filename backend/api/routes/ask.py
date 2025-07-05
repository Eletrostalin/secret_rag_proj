import logging
import time

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from backend.api.services.retrieval import retrieve_top_chunks
from backend.api.services.context_builder import build_context
from backend.api.services.prompt_engineering import generate_prompt
from backend.api.services.llm_client import call_llm

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.get("/", tags=["Ask"])
async def ask_endpoint(
    question: str = Query(..., description="Your question about HIPAA.", max_length=500)
):
    logger.info(f"Received question: {question}")

    try:
        total_start = time.time()

        # 1️⃣ Retrieval
        retrieval_start = time.time()
        top_chunks = await retrieve_top_chunks(question)
        retrieval_duration = time.time() - retrieval_start
        logger.info(f"Retrieved {len(top_chunks)} chunks in {retrieval_duration:.2f}s")

        if not top_chunks:
            return JSONResponse(content={"answer": "No relevant sections found.", "question": question})

        # 2️⃣ Context building
        context_start = time.time()
        context = build_context(top_chunks)
        context_duration = time.time() - context_start
        logger.info(f"Context built in {context_duration:.2f}s")

        # 3️⃣ Prompt engineering
        prompt_start = time.time()
        prompt = generate_prompt(question, context)
        prompt_duration = time.time() - prompt_start
        logger.info(f"Prompt generated in {prompt_duration:.2f}s")

        # 4️⃣ LLM call
        llm_start = time.time()
        answer = await call_llm(prompt)
        llm_duration = time.time() - llm_start
        logger.info(f"Answer received from LLM in {llm_duration:.2f}s")

        total_duration = time.time() - total_start
        logger.info(f"Total /ask duration: {total_duration:.2f}s")

        # 5️⃣ Response
        return JSONResponse(content={"answer": answer, "question": question})

    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))