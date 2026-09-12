FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt

COPY backend ./backend
COPY frontend ./frontend
COPY ml ./ml
COPY models ./models
COPY README.md .

RUN mkdir -p /data

EXPOSE 8000 8001
