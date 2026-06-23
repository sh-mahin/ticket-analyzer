FROM python:3.11-slim

# Phase 0: minimal stub. Model bake + DB deps land in Phase 1–2.

WORKDIR /app

# System deps kept minimal; build-essential not needed for the Phase 0 stub
# (torch / psycopg2 in later phases will add it back if required).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
