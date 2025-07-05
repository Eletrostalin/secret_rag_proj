import logging
from typing import List
from sentence_transformers import SentenceTransformer

# Логирование
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Название модели (можно вынести в конфиг)
MODEL_NAME = "all-MiniLM-L6-v2"

# Инициализация модели один раз при импорте
logger.info(f"Загружаем модель эмбеддингов: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
VECTOR_SIZE = model.get_sentence_embedding_dimension()
logger.info(f"Модель загружена. Размерность эмбеддинга: {VECTOR_SIZE}")


def embed_text(text: str) -> List[float]:
    """
    Преобразует один текст в эмбеддинг-вектор.
    """
    logger.debug("Генерация эмбеддинга для одного текста")
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Преобразует список текстов в список эмбеддинг-векторов.
    """
    logger.debug(f"Генерация эмбеддингов для батча из {len(texts)} текстов")
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()