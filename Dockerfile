# Используем официальный образ Python (лёгкая версия)
FROM python:3.12-slim

# Устанавливаем Tesseract OCR и русский язык
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-rus \
        tesseract-ocr-eng \
        libtesseract-dev && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую папку
WORKDIR /app

# Копируем список библиотек
COPY requirements.txt .

# Устанавливаем Python-библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY . .

# Запускаем бота
CMD ["python3", "bot.py"]



