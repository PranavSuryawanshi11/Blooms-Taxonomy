FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
WORKDIR /app/backend
ENV PORT=5000
EXPOSE 5000
CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:${PORT} app:app"]
