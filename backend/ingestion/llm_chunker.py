import json
import logging
from typing import List

from openai import OpenAI
from backend.db.schemas import ChunkData
from backend.config import OPENAI_API_KEY, OPENAI_MODEL

# Инициализация логгера
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Системное сообщение для LLM
SYSTEM_PROMPT = (
    "Ты юридический парсер. "
    "На входе будет сырой текст страницы или её фрагмента из PDF нормативного документа. "
    "На странице может быть несколько разделов (§). "
    "Разбей их на отдельные элементы массива. Каждый элемент описывает ровно один раздел или пункт закона. "
    "Если в одном разделе слишком много подпунктов или очень длинный текст — дели их на несколько объектов массива. "
    "Цель — чтобы каждый элемент массива был компактным, не больше нескольких абзацев. "
    "Твоя задача — структурировать это в формате JSON-массива, где каждый элемент — это словарь с полями:\n"
    "- part_number (или null)\n"
    "- subpart (или null)\n"
    "- section_number (обязательно)\n"
    "- parent_section_number (или null)\n"
    "- title (короткое название секции)\n"
    "- text (полный текст секции)\n"
    "- cross_references (список строк)\n\n"
    "Если part_number или subpart не указаны явно на странице, постарайся угадать их по контексту или нумерации секции (например, если секция начинается с 160., вероятно это Part 160). "
    "Если невозможно определить — верни null. "
    "Верни только корректный JSON-массив без пояснений и комментариев."
)


def clean_text(text: str) -> str:
    """
    Удаляет лишние пробелы и пустые строки.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def split_into_chunks(text: str, max_chars=800) -> List[str]:
    """
    Делит текст на куски не длиннее max_chars.
    Делает разрезы по абзацам.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > max_chars:
                # если параграф очень длинный — делим на фиксированные блоки
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i+max_chars].strip())
                current = ""
            else:
                current = para + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks


def call_llm_for_chunk(chunk_text: str, retries=2) -> List[ChunkData]:
    """
    Вызывает модель для одного небольшого куска текста.
    Делает до retries повторных попыток при ошибке парсинга.
    """
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Текст страницы или её фрагмента:\n{chunk_text}"
    )

    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"[LLM] Попытка {attempt}: Отправляем запрос ({len(chunk_text)} символов)")
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )

            content = response.choices[0].message.content
            logger.debug(f"[LLM] Ответ:\n{content}")

            parsed = json.loads(content)
            chunks = [ChunkData(**item) for item in parsed]
            return chunks

        except json.JSONDecodeError as e:
            logger.error(f"[LLM] Ошибка парсинга JSON (попытка {attempt}): {e}")
            logger.error(f"[LLM] Ответ модели был:\n{content}")
        except Exception as e:
            logger.error(f"[LLM] Ошибка запроса (попытка {attempt}): {e}")

    logger.error("[LLM] Все попытки обработки этого куска не удались")
    return []


def chunk_pages_llm(pages: List[str]) -> List[ChunkData]:
    """
    Обрабатывает список страниц PDF.
    Каждую длинную страницу делит на блоки ≤ 2000 символов.
    Для каждого блока вызывает модель.
    Подставляет последний найденный part_number и subpart, если модель вернула null.
    """
    all_chunks = []
    last_part = None
    last_subpart = None

    for page_number, page in enumerate(pages, start=1):
        logger.info(f"[LLM] Обрабатываем страницу {page_number} из {len(pages)}")

        # Чистим и режем страницу на блоки
        cleaned_page = clean_text(page)
        blocks = split_into_chunks(cleaned_page)

        logger.info(f"[LLM] Страница {page_number} разделена на {len(blocks)} блоков")

        for block_number, block in enumerate(blocks, start=1):
            logger.info(f"[LLM] Блок {block_number}/{len(blocks)} на странице {page_number}")

            chunk_results = call_llm_for_chunk(block)
            logger.info(f"[LLM] Получено чанков: {len(chunk_results)}")

            for chunk in chunk_results:
                if chunk.part_number:
                    last_part = chunk.part_number
                else:
                    chunk.part_number = last_part

                if chunk.subpart:
                    last_subpart = chunk.subpart
                else:
                    chunk.subpart = last_subpart

            all_chunks.extend(chunk_results)

    logger.info(f"[LLM] Всего чанков получено: {len(all_chunks)}")
    return all_chunks