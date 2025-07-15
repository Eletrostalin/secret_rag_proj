import asyncio
import json
import traceback

from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import logging

from backend.db.schemas import ChunkData

logger = logging.getLogger(__name__)


def remove_title_pages(input_path: str, output_path: str, skip_pages: int = 9):
    """
    Удаляет первые `skip_pages` страниц (титульный лист и оглавление).
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for i in range(skip_pages, len(reader.pages)):
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)

    logger.info(f"Удалены первые {skip_pages} страниц. Сохранено в {output_path}.")


def detect_page_types(pdf_path: str):
    """
    Проходит по всем страницам PDF и делит их на два вида:
    - Индекс-страницы (если PART встречается строго в первых 2 строках и нет SUBPART)
    - Обычные страницы с текстом закона
    Возвращает два списка кортежей (номер страницы, текст).
    """
    index_pages = []
    normal_pages = []

    with pdfplumber.open(pdf_path) as reader:
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = text.splitlines()

            # Проверяем только верхние 2 строки страницы
            TOP_N_LINES = 5
            is_index = any(
                line.strip().upper().startswith("PART") and "SUBPART" not in line.upper()
                for line in lines[:TOP_N_LINES]
            )

            if is_index:
                index_pages.append((i + 1, text))
            else:
                normal_pages.append((i + 1, text))

    return index_pages, normal_pages


def split_index_page_columns(page, threshold_left=180, threshold_right=300):
    """
    Делит страницу на три колонки по координатам X.
    Возвращает словарь с ключами 'left', 'center', 'right'.
    """
    words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    logger.debug(f"Найдено слов на странице: {len(words)}")

    left_words = []
    center_words = []
    right_words = []

    for word in words:
        x0 = word['x0']
        if x0 < threshold_left:
            left_words.append(word)
        elif x0 < threshold_right:
            center_words.append(word)
        else:
            right_words.append(word)

    def assemble_text(words_list):
        """
        Собирает текст из списка слов, группируя по Y.
        Разрывы абзацев определяются по адаптивному порогу на основе медианы расстояний.
        """
        if not words_list:
            return ""

        # Группировка по Y
        lines = {}
        for w in words_list:
            y = round(w['top'])
            if y not in lines:
                lines[y] = []
            lines[y].append((w['x0'], w['text']))

        sorted_lines = sorted(lines.items())

        # Считаем все интервалы по Y
        y_coords = [y for y, _ in sorted_lines]
        if len(y_coords) < 2:
            return "\n".join(" ".join(word for _, word in words) for _, words in sorted_lines)

        gaps = [y_coords[i] - y_coords[i - 1] for i in range(1, len(y_coords))]
        median_gap = sorted(gaps)[len(gaps) // 2]
        threshold_gap = median_gap * 1.5

        # Собираем текст с учетом разрывов
        text_lines = []
        prev_y = None
        for y, words in sorted_lines:
            words_sorted = sorted(words)  # сортируем слова слева направо по x0
            line_text = " ".join(w for _, w in words_sorted)

            if prev_y is not None and abs(y - prev_y) > threshold_gap:
                text_lines.append("")  # разрыв абзаца
            text_lines.append(line_text)
            prev_y = y

        return "\n".join(text_lines)

    return {
        "left": assemble_text(left_words),
        "center": assemble_text(center_words),
        "right": assemble_text(right_words)
    }


def remove_watermark_lines(text: str, watermark_lines=None) -> str:
    """
    Удаляет строки, содержащие любые из watermark_lines, из текста.
    """
    if watermark_lines is None:
        watermark_lines = [
            "HIPAA Administrative Simplification Regulation Text",
            "March 2013"
        ]

    lines = text.splitlines()
    cleaned_lines = [
        line for line in lines
        if all(wm.lower() not in line.lower() for wm in watermark_lines)
    ]
    return "\n".join(cleaned_lines)


def merge_index_columns(columns: dict) -> str:
    """
    Склеивает очищенные колонки в один итоговый текст.
    """
    left = columns.get("left", "").strip()
    center = columns.get("center", "").strip()
    right = columns.get("right", "").strip()

    parts = [left, center, right]
    return "\n\n".join(part for part in parts if part)


def clean_index_page_text(text: str) -> str:
    lower = text.lower()

    # 1) Удалить от Contents до SOURCE (не включая SOURCE)
    contents_idx = lower.find("contents")
    source_idx = lower.find("source")
    if contents_idx != -1 and source_idx != -1 and contents_idx < source_idx:
        text = text[:contents_idx] + text[source_idx:]
        lower = text.lower()  # обновляем для второго прохода

    # 2) Удалить от SOURCE (включительно) до следующего Subpart
    source_idx = lower.find("source")
    subpart_idx = lower.find("subpart")
    if source_idx != -1 and subpart_idx != -1 and source_idx < subpart_idx:
        text = text[:source_idx] + text[subpart_idx:]

    return text


def clean_normal_page(text: str) -> str:
    """
    Удаляет лишние переносы строк и пробелы.
    Склеивает строки в абзацы для более читаемого вида.
    """
    lines = text.splitlines()
    paragraphs = []
    current_paragraph = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
        else:
            current_paragraph.append(stripped)

    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return "\n\n".join(paragraphs)


async def parse_pdf(input_path: str, working_path: str):
    """
    Асинхронный пайплайн парсинга:
    - Удаление титульных страниц
    - Классификация страниц
    - Обработка страниц через split -> merge -> remove watermark -> clean
    - Возвращает список обработанных страниц в виде текста
    """
    logger.info("🟢 Шаг 1: Удаление титульных страниц...")
    await asyncio.to_thread(remove_title_pages, input_path, working_path)

    logger.info("🟢 Шаг 2: Классификация страниц (индекс / обычные)...")
    index_pages, normal_pages = await asyncio.to_thread(detect_page_types, working_path)

    total_index = len(index_pages)
    total_normal = len(normal_pages)

    logger.info(f"✅ Найдено индекс-страниц: {total_index}")
    logger.info(f"✅ Найдено обычных страниц: {total_normal}")

    processed_texts = []

    reader = await asyncio.to_thread(pdfplumber.open, working_path)

    # 🔵 Обработка индекс-страниц с прогрессом
    for i, (idx, _) in enumerate(index_pages, start=1):
        try:
            page = reader.pages[idx - 1]

            if page.extract_tables():
                logger.info(f"⚠️ [Индексная] Пропущена страница {idx} — обнаружена таблица")
                continue

            columns = await asyncio.to_thread(split_index_page_columns, page)
            merged = await asyncio.to_thread(merge_index_columns, columns)
            text_no_watermark = remove_watermark_lines(merged)

            # Специфичная очистка для индексных страниц
            cleaned = clean_index_page_text(text_no_watermark)
            normalized = clean_normal_page(cleaned)

            processed_texts.append(normalized)

            if i % 10 == 0 or i == total_index:
                percent = (i / total_index) * 100
                logger.info(f"📈 [Индексные страницы] Прогресс: {i}/{total_index} ({percent:.1f}%)")

        except Exception as e:
            logger.error(
                f"❌ Ошибка при обработке ИНДЕКСНОЙ страницы {idx}: {e}\n{traceback.format_exc()}"
            )

    # 🟢 Обработка обычных страниц с прогрессом
    for i, (idx, _) in enumerate(normal_pages, start=1):
        try:
            page = reader.pages[idx - 1]

            if page.extract_tables():
                logger.info(f"⚠️ [Обычная] Пропущена страница {idx} — обнаружена таблица")
                continue

            columns = await asyncio.to_thread(split_index_page_columns, page)
            merged = await asyncio.to_thread(merge_index_columns, columns)
            text_no_watermark = remove_watermark_lines(merged)

            # Обычные страницы не нуждаются в clean_index_page_text
            normalized = clean_normal_page(text_no_watermark)

            processed_texts.append(normalized)

            if i % 10 == 0 or i == total_normal:
                percent = (i / total_normal) * 100
                logger.info(f"📈 [Обычные страницы] Прогресс: {i}/{total_normal} ({percent:.1f}%)")

        except Exception as e:
            logger.error(
                f"❌ Ошибка при обработке ОБЫЧНОЙ страницы {idx}: {e}\n{traceback.format_exc()}"
            )

    logger.info("🎯 Парсинг PDF завершён успешно!")
    final_pages = []
    buffer = ""

    for page in processed_texts:
        if buffer:
            buffer += "\n\n" + page
        else:
            buffer = page

        if page.strip().endswith("]"):
            final_pages.append(buffer)
            buffer = ""

    if buffer:
        final_pages.append(buffer)

    return final_pages


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Использование: python parser.py <input.pdf> <output.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    parse_pdf(input_pdf, output_pdf)