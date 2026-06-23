"""Tickets router — Phase 1.

POST /tickets: validate, call the (stubbed) sentiment function, persist.
GET  /tickets: list newest-first with limit/offset pagination.
"""

from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/tickets", tags=["tickets"])


# --- Phase 1 stub: replaced by app.sentiment.predict() in Phase 2.
def fake_sentiment(message: str) -> tuple[str, float]:
    """Hardcoded sentiment — keeps DB correctness decoupled from model correctness."""
    return ("POSITIVE", 0.5)


@router.post(
    "",
    response_model=schemas.TicketOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    payload: schemas.TicketCreate,
    db: Session = Depends(get_db),
) -> schemas.TicketOut:
    sentiment, confidence = fake_sentiment(payload.message)
    ticket = crud.create_ticket(db, payload, sentiment, confidence)
    return schemas.TicketOut.model_validate(ticket)


@router.get(
    "",
    response_model=List[schemas.TicketOut],
)
def list_tickets(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[schemas.TicketOut]:
    tickets = crud.list_tickets(db, limit=limit, offset=offset)
    return [schemas.TicketOut.model_validate(t) for t in tickets]
