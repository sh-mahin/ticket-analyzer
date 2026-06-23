"""Health check router."""

from fastapi import APIRouter

from app import sentiment
from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Liveness probe.

    Returns `{"status": "ok", "model_loaded": <bool>}` so the cheapest
    possible canary for "is the demo about to fail?" is one curl away.
    """
    return HealthOut(status="ok", model_loaded=sentiment.is_loaded())
