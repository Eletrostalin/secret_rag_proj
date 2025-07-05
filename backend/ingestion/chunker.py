import re
from typing import List
from backend.db.schemas import ChunkData

# def extract_part_number(text: str) -> str | None:
#     """
#     Извлекает номер PART из текста страницы.
#     Ищет строку, начинающуюся с "PART", например "PART 160".
#     Возвращает строку вида "Part 160" или None, если не найдено.
#     """
#     for line in text.splitlines():
#         line = line.strip().upper()
#         if line.startswith("PART"):
#             match = re.match(r"PART\s*(\d+)", line)
#             if match:
#                 return f"Part {match.group(1)}"
#     return None


def get_part_from_section_number(section_number: str) -> str:
    """
    Извлекает номер Part из номера секции.
    Например § 160.102 => Part 160
    """
    match = re.match(r'^§\s*(\d{3})\.', section_number)
    if match:
        return f"Part {match.group(1)}"
    return "UNKNOWN"

# def extract_subpart(text: str) -> str | None:
#     """
#     Извлекает название SUBPART из текста страницы.
#     Ищет строку, начинающуюся с "SUBPART".
#     Возвращает полную строку, например "Subpart A—General Provisions", или None.
#     """
#     for line in text.splitlines():
#         line = line.strip()
#         if line.upper().startswith("SUBPART"):
#             return line
#     return None


def is_caps_title(line: str, threshold: float = 0.6) -> bool:
    """
    Проверяет, является ли строка капс-заголовком.
    threshold — минимальная доля заглавных букв.
    """
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    upper = sum(1 for c in letters if c.isupper())
    ratio = upper / len(letters)
    return ratio >= threshold


def split_by_sections(text: str) -> List[dict]:
    sections = []
    lines = text.splitlines()
    current_section_lines = []
    current_section_number = None
    in_new_paragraph = True

    for line in lines:
        line = line.strip()
        if not line:
            in_new_paragraph = True
            continue

        # Проверяем только начало абзаца (после пустой строки)
        if in_new_paragraph and line.startswith("§"):
            match = re.match(r"^(§\s*\d{3}\.\d+(?:\([^)]+\))?)\s+(.*)", line)
            if match:
                section_number = match.group(1)
                after_number = match.group(2).lstrip()

                # Проверка: первая буква после номера
                first_word_match = re.match(r"[A-Za-z]", after_number)
                if first_word_match and first_word_match.group(0).isupper():
                    # Это действительно заголовок новой секции
                    if current_section_number is not None:
                        sections.append({
                            "section_number": current_section_number,
                            "text": "\n".join(current_section_lines)
                        })
                    current_section_number = section_number
                    current_section_lines = [line]
                else:
                    # Это inline ссылка внутри текста — продолжаем старую секцию
                    if current_section_number is not None:
                        current_section_lines.append(line)
            else:
                # Строка с § без правильного формата
                if current_section_number is not None:
                    current_section_lines.append(line)
        else:
            # Продолжение текущей секции
            if current_section_number is not None:
                current_section_lines.append(line)

        in_new_paragraph = False

    # Добавляем последнюю секцию
    if current_section_number is not None:
        sections.append({
            "section_number": current_section_number,
            "text": "\n".join(current_section_lines)
        })

    return sections


def split_into_sections_from_pages(pages: List[str]) -> List[dict]:
    all_sections = []

    # current_part_number = None
    # current_subpart = None

    for page_text in pages:
        # part_number = extract_part_number(page_text)
        # subpart = extract_subpart(page_text)

        # if part_number:
        #     current_part_number = part_number
        # if subpart:
        #     current_subpart = subpart

        sections = split_by_sections(page_text)

        for section in sections:
            part_number = get_part_from_section_number(section["section_number"])
            section.update({
                "part_number": part_number,
                # "subpart": current_subpart,
                "cross_references": []
            })
            all_sections.append(section)

    return all_sections


def extract_cross_references(text: str, section_number: str) -> List[str]:
    """
    Извлекает все упоминания других § из текста секции.
    - Находит все шаблоны вида § 160.XXX
    - Исключает ссылки на саму себя
    Возвращает отсортированный список уникальных ссылок.
    """
    pattern = r"§\s*(\d{3}\.\d+(?:\([^)]+\))?)"
    matches = re.findall(pattern, text)
    found = set()

    for m in matches:
        # Исключаем self-ссылку на эту же секцию
        if m.startswith(section_number.replace('§', '').strip()):
            continue
        found.add(m)

    return sorted(found)


def flatten_paragraphs(text: str) -> str:
    """
    Заменяет переносы строк внутри абзацев на пробелы.
    Разрывы абзацев (два \n подряд) оставляет.
    """
    paragraphs = text.split("\n\n")
    flattened = []
    for p in paragraphs:
        lines = [line.strip() for line in p.splitlines() if line.strip()]
        flattened.append(" ".join(lines))
    return "\n\n".join(flattened)


def build_chunk(section_dict: dict) -> ChunkData:
    """
    Преобразует словарь с данными секции в объект ChunkData.
    Вычисляет:
      - part_number
      # - subpart
      - section_number
      - текст секции (с удалением лишних переносов строк внутри абзацев)
      - список cross_references
    """
    raw_text = section_dict.get("text", "")
    cleaned_text = flatten_paragraphs(raw_text)

    return ChunkData(
        part_number=section_dict.get("part_number"),
        # subpart=section_dict.get("subpart"),
        section_number=section_dict.get("section_number", "UNKNOWN"),
        text=cleaned_text,
        cross_references=section_dict.get("cross_references", [])
    )


def chunk_texts_to_chunks(pages: List[str]) -> List[ChunkData]:
    """
    Финальный пайплайн чанкования:
    - Делит список текстов страниц на отдельные секции
    - Для каждой секции извлекает cross_references
    - Преобразует секции в объекты ChunkData
    Возвращает итоговый список чанков.
    """
    all_sections = split_into_sections_from_pages(pages)
    chunks = []
    for section in all_sections:
        # Извлекаем кросс-ссылки из текста секции
        section["cross_references"] = extract_cross_references(section["text"], section["section_number"])
        # Преобразуем в объект ChunkData
        chunk = build_chunk(section)
        chunks.append(chunk)
    return chunks