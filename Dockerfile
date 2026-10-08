FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY tests ./tests
COPY docs ./docs

RUN pip install --upgrade pip && pip install .

RUN useradd --create-home --uid 10001 appuser &&     mkdir -p /app/generated_resumes &&     chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
