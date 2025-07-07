import gradio as gr
import requests

BACKEND_URL = "http://backend:8000"

def ask_question(question):
    if not question.strip():
        return "❌ Введите вопрос."

    try:
        response = requests.get(f"{BACKEND_URL}/ask/", params={"question": question}, timeout=60)
        if response.ok:
            data = response.json()
            return f"**Q:** {data.get('question')}\n\n**A:** {data.get('answer')}"
        else:
            return f"❌ Ошибка сервера: {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ Ошибка запроса: {str(e)}"


def upload_pdf_file(file):
    if file is None:
        return "❌ Выберите PDF файл."

    try:
        with open(file.name, "rb") as f:
            files = {"file": (file.name, f, "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=300)

        if response.ok:
            data = response.json()
            return f"✅ PDF успешно обработан. Добавлено чанков: {data.get('chunks')}"
        else:
            return f"❌ Ошибка загрузки: {response.status_code} - {response.text}"

    except Exception as e:
        return f"❌ Ошибка отправки файла: {str(e)}"


with gr.Blocks(title="HIPAA RAG UI") as demo:
    gr.Markdown("# HIPAA Retrieval-Augmented QA")

    with gr.Tab("Задать вопрос"):
        question_input = gr.Textbox(label="Введите ваш вопрос")
        answer_output = gr.Markdown(label="Ответ")
        send_button = gr.Button("Отправить")

        send_button.click(
            fn=ask_question,
            inputs=question_input,
            outputs=answer_output
        )

    with gr.Tab("Загрузить PDF"):
        pdf_input = gr.File(label="Выберите PDF", file_types=[".pdf"])
        upload_output = gr.Markdown(label="Статус загрузки")
        upload_button = gr.Button("Загрузить PDF")

        upload_button.click(
            fn=upload_pdf_file,
            inputs=pdf_input,
            outputs=upload_output
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)