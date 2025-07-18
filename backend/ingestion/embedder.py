import logging
from typing import List
from sentence_transformers import SentenceTransformer

# Логирование
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Название модели — можно вынести в переменные окружения
MODEL_NAME = "intfloat/multilingual-e5-large" # перешел на эту с all-MiniLM-L6-v2

# Инициализация модели один раз при импорте
logger.info(f"Загружаем модель эмбеддингов: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
VECTOR_SIZE = model.get_sentence_embedding_dimension()
logger.info(f"Модель загружена. Размерность эмбеддинга: {VECTOR_SIZE}")


def embed_text(text: str, is_query: bool = True) -> List[float]:
    """
    Преобразует один текст в эмбеддинг-вектор.
    Добавляет префикс 'query: ' или 'passage: ' в зависимости от контекста.
    """
    prefix = "query: " if is_query else "passage: "
    logger.debug(f"Генерация эмбеддинга для одного текста с префиксом '{prefix.strip()}'")
    embedding = model.encode(prefix + text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str], is_query: bool = False) -> List[List[float]]:
    """
    Преобразует список текстов в список эмбеддинг-векторов.
    Добавляет префикс 'passage: ' или 'query: ' к каждому элементу.
    """
    prefix = "query: " if is_query else "passage: "
    logger.debug(f"Генерация эмбеддингов для батча из {len(texts)} текстов с префиксом '{prefix.strip()}'")
    prefixed_texts = [prefix + text for text in texts]
    embeddings = model.encode(prefixed_texts, convert_to_numpy=True)
    return embeddings.tolist()