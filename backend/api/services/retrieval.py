import logging
import numpy as np
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.services.filter_chunks_via_llm import rerank_chunks_via_llm
from backend.api.services.llm_client import call_llm
from backend.db.database import async_session
from backend.db.models import Chunk
from backend.ingestion.embedder import embed_text
from backend.prompts import QUERY_EXPANSION_PROMPT_TEMPLATE, QUERY_REWRITING_PROMPT_TEMPLATE


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



async def retrieve_top_chunks(question: str, session: AsyncSession = None) -> List[Chunk]:
    logger.info(f"Начинаем поиск по запросу: {question}")

    if session is None:
        async with async_session() as session:
            return await retrieve_top_chunks(question, session)

    # 🔁 Переписываем запрос (только для BM25)
    rewritten_query = await rewrite_query_llm(question)
    logger.info(f"Rewritten query for BM25: {rewritten_query}")

    # 1️⃣ BM25 Retrieval (использует expansion внутри)
    bm25_chunks = await bm25_search(session, rewritten_query)
    logger.info(f"BM25 найдено кандидатов: {len(bm25_chunks)}")

    if not bm25_chunks:
        logger.warning("BM25 ничего не вернул. Fallback: все чанки из БД")
        result = await session.execute(select(Chunk))
        bm25_chunks = result.scalars().all()
        if not bm25_chunks:
            logger.error("В БД нет чанков.")
            return []

    # 2️⃣ Dense embedding rerank (использует 🟢 сырой вопрос)
    top_chunks = await embedding_rerank(rewritten_query, bm25_chunks, top_n=10)
    logger.info(f"Топ после cosine rerank: {len(top_chunks)}")

    # 3️⃣ LLM rerank
    chunk_texts = [chunk.text for chunk in top_chunks]
    reranked_indices = await rerank_chunks_via_llm(question, chunk_texts)

    if not reranked_indices:
        logger.warning("LLM не вернул порядок чанков. Используем cosine top-N как fallback.")
        return top_chunks[:6]  # fallback

    # 4️⃣ Финальные чанки после LLM rerank
    final_chunks = [top_chunks[i - 1] for i in reranked_indices if 0 < i <= len(top_chunks)][:6]
    logger.info(f"Финальные чанки после LLM rerank: {len(final_chunks)}")

    return final_chunks


async def bm25_search(session: AsyncSession, rewritten_query: str, limit: int = 80) -> List[Chunk]:
    """
    Поиск в PostgreSQL по bm25_text.
    Использует только переписанный запрос без expansion.
    """
    # Удаляем стоп-слова из переписанного запроса (на всякий случай)
    cleaned_terms = remove_stopwords(rewritten_query)
    if not cleaned_terms:
        logger.warning("После удаления стоп-слов из переписанного запроса ничего не осталось.")
        return []

    # 🚫 Expansion отключён
    tsquery_string = " | ".join(cleaned_terms)
    logger.info(f"🔍 BM25 final tsquery (no expansion): {tsquery_string}")
    tsquery = func.to_tsquery('english', tsquery_string)

    stmt = (
        select(Chunk)
        .where(Chunk.bm25_text.op('@@')(tsquery))
        .order_by(func.ts_rank_cd(Chunk.bm25_text, tsquery).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    chunks = result.scalars().all()
    return chunks

def remove_stopwords(text: str) -> List[str]:
    """
    Удаляет очень частые стоп-слова (очень простой список для примера).
    """
    stopwords = {
        "what", "is", "the", "a", "an", "of", "in", "on", "for", "and", "to", "with", "about", "which", "does", "can", "i"
    }
    tokens = [word.lower() for word in text.split()]
    cleaned = [word for word in tokens if word not in stopwords]
    return cleaned


async def rewrite_query_llm(question: str) -> str:
    """
    Делает запрос в LLM для переформулировки запроса.
    """

    logger.info("Calling LLM for query rewriting")
    prompt = QUERY_REWRITING_PROMPT_TEMPLATE.format(question=question)

    try:
        rewritten = await call_llm(prompt)
        logger.debug(f"LLM rewritten query: {rewritten}")
        return rewritten.strip()

    except Exception as e:
        logger.error(f"Error during query rewriting LLM call: {e}")
        return question  # fallback: вернуть оригинальный


async def expand_query_terms_llm(text: str) -> List[str]:
    """
    Делает запрос в LLM для query expansion на основе переформулированного текста.
    """

    logger.info("Calling LLM for query expansion")
    prompt = QUERY_EXPANSION_PROMPT_TEMPLATE.format(question=text)

    try:
        response = await call_llm(prompt)
        logger.debug(f"Raw LLM expansion response: {response}")

        terms = [term.strip() for term in response.replace(",", " ").split() if term.strip()]
        return terms

    except Exception as e:
        logger.error(f"Error during query expansion LLM call: {e}")
        return []


async def embedding_rerank(query_for_embedding: str, bm25_chunks: List[Chunk], top_n: int = 10) -> List[Chunk]:
    """
    Семантический rerank:
    - сортирует все чанки по cosine similarity,
    - отбирает те, что >= MIN_SIMILARITY_THRESHOLD,
    - если их достаточно — возвращает top_n отфильтрованных,
    - иначе — fallback: top_n самых близких без порога.
    """
    logger.debug("Генерация эмбеддинга для запроса")
    query_embedding = np.array(embed_text(query_for_embedding))

    scored_chunks = []
    for chunk in bm25_chunks:
        if chunk.embedding_vector is None:
            continue
        chunk_vector = np.array(chunk.embedding_vector)
        score = cosine_similarity(query_embedding, chunk_vector)
        scored_chunks.append((chunk, score))

    if not scored_chunks:
        logger.warning("❌ Нет чанков с эмбеддингами")
        return []

    # Сортировка по убыванию схожести
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # 📊 Логирование статистики
    scores = [score for _, score in scored_chunks]
    logger.info(f"📈 Cosine stats — max: {max(scores):.4f}, min: {min(scores):.4f}, avg: {np.mean(scores):.4f}")

    # Пороговая фильтрация
    MIN_SIMILARITY_THRESHOLD = 0.8
    filtered_chunks = [chunk for chunk, score in scored_chunks if score >= MIN_SIMILARITY_THRESHOLD]

    section_ids = [chunk.section_number or "??" for chunk in filtered_chunks]

    logger.info(
        f"🎯 Отобрано {len(filtered_chunks)} чанков с cosine ≥ {MIN_SIMILARITY_THRESHOLD} — §§ {', '.join(section_ids)}")

    if len(filtered_chunks) >= top_n:
        return filtered_chunks[:top_n]
    else:
        logger.warning("⚠️ Недостаточно релевантных чанков, используем fallback на top-N")
        return [chunk for chunk, _ in scored_chunks[:top_n]]


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Простая и стабильная косинусная схожесть.
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)


