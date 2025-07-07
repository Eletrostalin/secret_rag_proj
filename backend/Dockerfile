FROM python:3.12

# Устанавливаем рабочую директорию прямо в корень проекта внутри контейнера
COPY ../ /code

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё в /code
COPY . .

# Запуск uvicorn из /code
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]