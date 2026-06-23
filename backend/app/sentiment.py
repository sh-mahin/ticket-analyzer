"""Sentiment model wrapper.

Phase 1: stub. `load_model()` is a no-op and `predict()` is unused
(POST /tickets still calls the fake_sentiment() stub in routers/tickets).
Phase 2 replaces this with the real distilbert pipeline and updates the
router to call `predict()`.
"""

from typing import Tuple

# Module-level state — assigned by load_model(), read by predict().
_pipeline = None


def load_model() -> None:
    """Initialize the inference pipeline.

    Phase 1: no-op. Phase 2: build a transformers pipeline and assert
    id2label resolves to exactly {POSITIVE, NEGATIVE}.
    """
    global _pipeline
    _pipeline = None  # explicit — visible in logs and tests


def is_loaded() -> bool:
    return _pipeline is not None


def predict(text: str) -> Tuple[str, float]:
    """Run sentiment inference on `text`.

    Phase 1: should not be reached. The router still uses fake_sentiment().
    Phase 2: real implementation, returning (label, rounded_score).
    """
    raise RuntimeError(
        "sentiment.predict() is not implemented in Phase 1; "
        "the router is still using fake_sentiment()."
    )
