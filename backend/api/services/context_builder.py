import logging
from typing import List
from backend.db.models import Chunk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def build_context(chunks: List[Chunk]) -> str:
    """
    Собирает текстовый контекст из списка чанков.
    Каждый чанк красиво размечен с § и Part.
    """
    logger.info(f"Формируем контекст из {len(chunks)} чанков")

    context_lines = []
    for chunk in chunks:
        part = chunk.part_number or "UNKNOWN PART"
        section = chunk.section_number or "UNKNOWN SECTION"
        text = chunk.text.strip()

        context_lines.append(f"§ {section} ({part})\n{text}\n")

    context_text = "\n".join(context_lines)

    logger.debug(f"Готовый контекст ({len(context_text)} символов)")
    return context_text