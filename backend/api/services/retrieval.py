import logging
import numpy as np
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.services.llm_client import call_llm
from backend.db.database import async_session
from backend.db.models import Chunk
from backend.ingestion.embedder import embed_text
from backend.prompts import QUERY_EXPANSION_PROMPT_TEMPLATE, QUERY_REWRITING_PROMPT_TEMPLATE


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def retrieve_top_chunks(question: str, session: AsyncSession = None) -> List[Chunk]:
    """
    Главная функция retrieval.
    На входе: вопрос (строка).
    На выходе: топовые чанки (список моделей Chunk).
    """
    logger.info(f"Начинаем поиск по запросу: {question}")

    if session is None:
        async with async_session() as session:
            return await retrieve_top_chunks(question, session)

    # 1️⃣ BM25 Retrieval
    bm25_chunks = await bm25_search(session, question)
    logger.info(f"BM25 найдено кандидатов: {len(bm25_chunks)}")

    if not bm25_chunks:
        logger.warning("BM25 ничего не вернул. Пробуем fallback на все чанки.")
        # Fallback: загрузить все
        result = await session.execute(select(Chunk))
        bm25_chunks = result.scalars().all()
        logger.info(f"⚠️ Fallback-режим: загружено {len(bm25_chunks)} всех чанков из БД для дальнейшего rerank.")

        if not bm25_chunks:
            logger.error("Вообще нет данных в таблице chunks!")
            return []

    # 2️⃣ Dense reranking
    top_chunks = await embedding_rerank(question, bm25_chunks)
    logger.info(f"Финальный топ после rerank: {len(top_chunks)}")

    return top_chunks


async def bm25_search(session: AsyncSession, question: str, limit: int = 100) -> List[Chunk]:
    """
    Поиск в PostgreSQL по bm25_text.
    Использует LLM для rewriting и expansion.
    """
    # Удаляем стоп-слова
    cleaned_terms = remove_stopwords(question)
    if not cleaned_terms:
        logger.warning("После удаления стоп-слов ничего не осталось.")
        return []

    # Шаг 1: Rewriting
    rewritten_query = await rewrite_query_llm(" ".join(cleaned_terms))
    logger.info(f"Rewritten query: {rewritten_query}")

    if not rewritten_query:
        logger.warning("LLM не вернул переписанный запрос.")
        return []

    # Шаг 2: Expansion
    expanded_terms = await expand_query_terms_llm(rewritten_query)
    if not expanded_terms:
        logger.warning("LLM не вернул expansion terms.")
        return []

    # OR-запрос
    tsquery_string = " | ".join(expanded_terms)
    logger.info(f"BM25 tsquery: {tsquery_string}")

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


async def embedding_rerank(question: str, bm25_chunks: List[Chunk], top_n: int = 5) -> List[Chunk]:
    """
    Семантический rerank: сортировка по cosine similarity.
    """
    logger.debug("Генерация эмбеддинга для вопроса")
    query_embedding = np.array(embed_text(question))

    scored_chunks = []
    for chunk in bm25_chunks:
        if chunk.embedding_vector is None:
            continue
        chunk_vector = np.array(chunk.embedding_vector)
        score = cosine_similarity(query_embedding, chunk_vector)
        scored_chunks.append((chunk, score))

    # Сортировка по убыванию схожести
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # Топ-N результатов
    top_chunks = [chunk for chunk, score in scored_chunks[:top_n]]
    return top_chunks


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Простая и стабильная косинусная схожесть.
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)