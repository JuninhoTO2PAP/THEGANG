FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p uploads /app/data

EXPOSE 8000

# Normaliza DATABASE_URL do Render antes do Alembic/API (psycopg v3).
# Seed opcional com SEED_ON_BOOT=1.
CMD ["sh", "-c", "\
  if [ -n \"$DATABASE_URL\" ]; then \
    case \"$DATABASE_URL\" in \
      postgres://*) export DATABASE_URL=\"postgresql+psycopg://${DATABASE_URL#postgres://}\" ;; \
      postgresql://*) export DATABASE_URL=\"postgresql+psycopg://${DATABASE_URL#postgresql://}\" ;; \
    esac; \
  fi; \
  alembic upgrade head && \
  if [ \"$SEED_ON_BOOT\" = \"1\" ]; then python -m app.db.seed || true; fi && \
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
