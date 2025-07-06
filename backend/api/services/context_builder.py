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
    logger.info(f"=== Формируем контекст из {len(chunks)} чанков ===")

    if not chunks:
        logger.warning("⚠️ Пустой список чанков для контекста!")
        return ""

    context_lines = []
    for chunk in chunks:
        part = chunk.part_number or "UNKNOWN PART"
        section = chunk.section_number or "UNKNOWN SECTION"
        text = chunk.text.strip()

        context_lines.append(f"§ {section} ({part})\n{text}\n")

    context_text = "\n".join(context_lines)

    # Логируем первые 2000 символов
    preview_length = 2000
    logger.info(f"CONTEXT BUILD COMPLETE. Длина: {len(context_text)} символов.")
    logger.info(f"CONTEXT PREVIEW (первые {preview_length} символов):\n{context_text[:preview_length]}")

    return context_text