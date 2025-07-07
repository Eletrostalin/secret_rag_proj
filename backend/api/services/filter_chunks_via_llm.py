import logging
from typing import List
from backend.api.services.llm_client import call_llm
from backend.prompts import FILTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def filter_chunks_via_llm(question: str, top_chunks: List[str]) -> List[int]:
    """
    Asks the LLM to pick which of the retrieved chunks contain the exact quoted regulation text needed for the question.

    Returns a list of selected indices (1-based).
    """
    try:
        logger.info("=== FilterChunks via LLM started ===")
        logger.info(f"Question: {question}")
        logger.info(f"Received {len(top_chunks)} chunks for filtering.")

        # 1️⃣ Number and format the chunks
        numbered_chunks_lines = []
        for idx, chunk in enumerate(top_chunks, start=1):
            numbered_chunks_lines.append(f"{idx}. {chunk.strip()}")

        numbered_chunks_text = "\n\n".join(numbered_chunks_lines)
        logger.debug(f"Numbered chunks:\n{numbered_chunks_text[:2000]}")

        # 2️⃣ Build the user prompt
        user_prompt = (
            f"QUESTION: {question}\n\n"
            f"CHUNKS:\n{numbered_chunks_text}\n\n"
            f"INSTRUCTIONS: Identify which chunks contain the exact legal regulation text answering the question."
        )

        # 3️⃣ Combine system + user for call
        full_prompt = f"{FILTER_SYSTEM_PROMPT}\n\n=== QUESTION ===\n{user_prompt}"

        logger.debug(f"Final prompt for LLM (first 2000 chars):\n{full_prompt[:2000]}")

        # 4️⃣ Call LLM
        llm_response = await call_llm(full_prompt)
        logger.info(f"Raw LLM response: '{llm_response}'")

        # 5️⃣ Parse response: expecting comma-separated numbers
        selected_indices = []
        if llm_response.strip():
            parts = llm_response.strip().split(",")
            for part in parts:
                part = part.strip()
                if part.isdigit():
                    selected_indices.append(int(part))
                else:
                    logger.warning(f"Non-numeric part in LLM response: '{part}'")

        logger.info(f"Selected chunk numbers: {selected_indices}")

        return selected_indices

    except Exception as e:
        logger.error(f"Error in filter_chunks_via_llm: {e}", exc_info=True)
        return []
