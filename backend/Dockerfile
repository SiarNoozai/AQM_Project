FROM python:3.12-slim

WORKDIR /app

# Nur Metadaten zuerst kopieren -> Docker-Layer-Cache fuer Dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

COPY *.py ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
