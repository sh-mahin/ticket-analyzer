FROM python:3.11-slim

# Phase 2: bake the real distilbert model into the image so the container
# can boot with TRANSFORMERS_OFFLINE=1 (i.e. with --network none).
#
# Bake-time online + runtime offline pattern:
#   * Build stage:  TRANSFORMERS_OFFLINE=0, HF_HOME=/opt/hf-cache
#     The bake RUN below is the only step that may hit the network.
#   * Runtime:      TRANSFORMERS_OFFLINE=1 is set as a final ENV so the
#     container can never silently re-fetch at startup or per-request.

WORKDIR /app

# System deps: ca-certificates for HTTPS model download, build-essential +
# libpq-dev for psycopg2-binary wheel fallback (not strictly needed on slim
# but cheap to keep), and curl for the optional offline-boot smoke test.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- Bake-time env: TRANSFORMERS_OFFLINE is explicitly 0 so the download works.
ENV HF_HOME=/opt/hf-cache \
    TRANSFORMERS_OFFLINE=0

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Bake the distilbert SST-2 model + tokenizer into /opt/hf-cache.
# This is the ONLY step in the whole image that touches the network.
# `text` argument triggers tokenizer download; `from_pretrained` on the
# model class triggers weight download. Both land in $HF_HOME.
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    name='distilbert-base-uncased-finetuned-sst-2-english'; \
    AutoTokenizer.from_pretrained(name); \
    AutoModelForSequenceClassification.from_pretrained(name); \
    print('baked:', name)"

COPY app ./app

# --- Runtime env: flip the switch. From here down, the container must
# never try to reach the HuggingFace hub.
ENV TRANSFORMERS_OFFLINE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
