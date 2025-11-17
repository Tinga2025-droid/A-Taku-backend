FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copia apenas requirements primeiro
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copia somente o necessário
COPY app ./app
COPY render.yaml .
COPY .env.example .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]