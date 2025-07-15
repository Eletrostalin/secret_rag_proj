import gradio as gr
import requests
import time

BACKEND_URL = "http://backend:8000"

def ask_question(question):
    if not question.strip():
        return "❌ Введите вопрос."

    try:
        response = requests.get(f"{BACKEND_URL}/ask/", params={"question": question}, timeout=1800)
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
        # 1️⃣ Старт загрузки файла
        with open(file.name, "rb") as f:
            files = {"file": (file.name, f, "application/pdf")}
            response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=60)

        if not response.ok:
            return f"❌ Ошибка загрузки: {response.status_code} - {response.text}"

        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            return "❌ Сервер не вернул task_id"

        # 2️⃣ Polling статус
        status_url = f"{BACKEND_URL}/upload/status"
        max_poll_attempts = 180  # 180*5 = 15 минут макс ожидания
        poll_interval = 5  # секунд

        for attempt in range(max_poll_attempts):
            time.sleep(poll_interval)
            status_resp = requests.get(status_url, params={"task_id": task_id}, timeout=30)
            if not status_resp.ok:
                continue

            status_data = status_resp.json()
            status = status_data.get("status")

            if status == "DONE":
                chunks = status_data.get("result", {}).get("chunks", "unknown")
                return f"✅ PDF успешно обработан. Добавлено чанков: {chunks}"
            elif status == "ERROR":
                error_msg = status_data.get("error", "Неизвестная ошибка")
                return f"❌ Ошибка при обработке PDF: {error_msg}"
            else:
                # статус PENDING
                yield f"⏳ Идёт обработка... {attempt * poll_interval} секунд прошло"

        return "❌ Таймаут ожидания обработки PDF. Попробуйте позже."

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