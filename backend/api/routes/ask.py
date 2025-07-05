from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import logging

from backend.retrieval import retrieve_top_chunks
from backend.context_builder import build_context
from backend.prompt_engineering import generate_prompt
from backend.llm_client import call_llm

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/ask")
async def ask_endpoint(question: str = Query(..., description="Your question about HIPAA.")):
    logger.info(f"Received question: {question}")

    try:
        # 1️⃣ Retrieval
        top_chunks = await retrieve_top_chunks(question)
        logger.info(f"Retrieved {len(top_chunks)} chunks")

        # 2️⃣ Context building
        context = build_context(top_chunks)
        logger.info("Context built")

        # 3️⃣ Prompt engineering
        prompt = generate_prompt(question, context)
        logger.info("Prompt generated")

        # 4️⃣ LLM call
        answer = await call_llm(prompt)
        logger.info("Answer received from LLM")

        # 5️⃣ Response
        return JSONResponse(content={"answer": answer, "question": question})

    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))