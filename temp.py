from PyPDF2 import PdfReader, PdfWriter

def slice_pdf(input_path, output_path, start=0, end=80):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Ограничим до конца файла
    end = min(end, len(reader.pages))

    for i in range(start, end):
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Сохранён файл {output_path} с {end - start} страницами.")

# Пример вызова
slice_pdf("hipaa-combined.pdf", "hipaa-combined80.pdf", 0, 80)