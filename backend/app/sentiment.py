"""Sentiment model wrapper.

Phase 2: real distilbert-base-uncased-finetuned-sst-2-english pipeline,
loaded once at app startup (called from `app.main` lifespan). Designed to
work with `TRANSFORMERS_OFFLINE=1` + a pre-populated `HF_HOME`.

Public surface:
    load_model() -> None     — build the pipeline; idempotent at runtime
    is_loaded()  -> bool     — module-level loaded flag for /health
    predict(text) -> (label, score) tuple
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from transformers import pipeline

logger = logging.getLogger(__name__)

MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

# Module-level state — assigned by load_model(), read by predict() and /health.
_pipeline = None


def _assert_label_sanity(pipe) -> None:
    """Fail fast if the underlying model's id2label is not exactly
    {POSITIVE, NEGATIVE} (case-sensitive, no LABEL_0 / LABEL_1).

    distilbert-base-uncased-finetuned-sst-2-english ships with the right
    mapping, but a future swap of MODEL_NAME could silently regress.
    """
    model = getattr(pipe, "model", None)
    if model is None:
        raise RuntimeError("pipeline has no .model attribute; cannot verify labels")

    id2label = getattr(model.config, "id2label", None)
    if not id2label:
        raise RuntimeError(
            f"Model {MODEL_NAME} has no id2label mapping; "
            "refusing to load because the API contract assumes {POSITIVE, NEGATIVE}."
        )

    labels = set(id2label.values())
    expected = {"POSITIVE", "NEGATIVE"}
    if labels != expected:
        raise RuntimeError(
            f"Model {MODEL_NAME} id2label is {sorted(labels)}; "
            f"expected exactly {sorted(expected)}. "
            "Switching models requires updating the API contract."
        )


def load_model() -> None:
    """Initialize the inference pipeline (idempotent at runtime).

    Called from `app.main` lifespan, AFTER schema bootstrap and BEFORE
    the first request. Idempotent: a second call is a no-op so unit
    tests / double-imports don't pay the cost twice.
    """
    global _pipeline
    if _pipeline is not None:
        logger.info("sentiment.load_model: already loaded, skipping")
        return

    logger.info("sentiment.load_model: building pipeline for %s", MODEL_NAME)
    pipe = pipeline(
        task="sentiment-analysis",
        model=MODEL_NAME,
        # tokenizer defaults to the same name as the model — explicit is
        # clearer for the workshop audience reading the code.
        tokenizer=MODEL_NAME,
        # Force CPU. The workshop VM does not have a GPU; torch device
        # autodetection would also pick CPU here, but being explicit
        # avoids surprises if the image is ever run on a GPU host.
        device=-1,
        # Single-item batches — the router handles one ticket at a time.
        batch_size=1,
    )
    _assert_label_sanity(pipe)

    _pipeline = pipe
    logger.info("sentiment.load_model: OK — id2label=%s", dict(pipe.model.config.id2label))


def is_loaded() -> bool:
    return _pipeline is not None


def predict(text: str) -> Tuple[str, float]:
    """Run sentiment inference on `text`.

    Truncates to 512 tokens implicitly via the tokenizer's truncation=True
    default; we additionally clip the raw string to 4000 chars upstream
    (TicketCreate validation), so this is a belt-and-braces guard.

    Returns (label, confidence) where label is "POSITIVE" or "NEGATIVE"
    and confidence is rounded to 3 decimals.
    """
    if _pipeline is None:
        raise RuntimeError(
            "sentiment.predict() called before load_model(); "
            "lifespan startup hook is broken."
        )

    # transformers returns [{"label": "POSITIVE", "score": 0.9876}, ...]
    result = _pipeline(text[:512])[0]
    label = result["label"]
    score = float(result["score"])
    return label, round(score, 3)


# Optional manual reset hook for tests / REPL; never called from app code.
def _reset_for_tests() -> None:
    global _pipeline
    _pipeline = None
