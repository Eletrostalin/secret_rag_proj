import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.api.services.classifier import classify_request
from backend.api.services.quote_handler import handle_quote_request
from backend.api.services.retrieval import retrieve_top_chunks
from backend.api.services.context_builder import build_context
from backend.api.services.prompt_engineering import generate_prompt
from backend.api.services.llm_client import call_llm

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.get("/", tags=["Ask"])
async def ask_endpoint(question: str):
    logger.info(f"Received question: {question}")

    try:
        total_start = time.time()

        # 0️⃣ Классификация
        classification_start = time.time()
        result = await classify_request(question)
        mode = result["mode"]
        section = result["target_section"]
        classification_duration = time.time() - classification_start
        logger.info(f"Classification: mode={mode}, section={section} (took {classification_duration:.2f}s)")

        # 🔁 QUOTE mode (возможно, с номером параграфа)
        if mode == "QUOTE":
            quote_start = time.time()
            quote_answer = await handle_quote_request(question, section)
            quote_duration = time.time() - quote_start
            logger.info(f"QUOTE handler completed in {quote_duration:.2f}s")

            return JSONResponse(content={"answer": quote_answer, "question": question, "mode": "QUOTE"})

        # 1️⃣ Retrieval
        retrieval_start = time.time()
        top_chunks = await retrieve_top_chunks(question)
        retrieval_duration = time.time() - retrieval_start
        logger.info(f"Retrieved {len(top_chunks)} chunks in {retrieval_duration:.2f}s")

        if not top_chunks:
            return JSONResponse(
                content={"answer": "No relevant sections found.", "question": question, "mode": "NORMAL"}
            )

        # 💬 Логируем номера всех § в контексте
        valid_section_numbers = [chunk.section_number for chunk in top_chunks]
        logger.info(f"🔎 Контекст содержит следующие section_number: {valid_section_numbers}")

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
        answer = await call_llm(prompt, purpose="answer")
        llm_duration = time.time() - llm_start
        logger.info(f"Answer received from LLM in {llm_duration:.2f}s")

        total_duration = time.time() - total_start
        logger.info(f"Total /ask duration: {total_duration:.2f}s")

        return JSONResponse(content={"answer": answer, "question": question, "mode": "NORMAL"})

    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))