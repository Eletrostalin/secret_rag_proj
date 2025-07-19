import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()


# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_ANSWER = os.getenv("OPENAI_MODEL_ANSWER", "gpt-4.1")
OPENAI_MODEL_CLASSIFY = os.getenv("OPENAI_MODEL_CLASSIFY", "gpt-4o-mini")
OPENAI_MODEL_REWRITE = os.getenv("OPENAI_MODEL_REWRITE", "gpt-4o")
OPENAI_MODEL_EXPAND = os.getenv("OPENAI_MODEL_EXPAND", "gpt-4o")
OPENAI_MODEL_FILTER = os.getenv("OPENAI_MODEL_FILTER", "gpt-4.1")
OPENAI_MODEL_RERANK = os.getenv("OPENAI_MODEL_RERANK", "gpt-4.1")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env или переменных окружения")

# Postgres
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST]):
    raise ValueError("Не все параметры подключения к Postgres найдены в .env")

# Полный URL для SQLAlchemy
DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)