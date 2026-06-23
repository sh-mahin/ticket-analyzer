"""Database access functions for tickets.

The DB layer is intentionally thin — it only knows how to translate between
Pydantic input and ORM rows; sentiment is provided by the caller so the
fake (Phase 1) and real (Phase 2) implementations are interchangeable.
"""

from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


def create_ticket(
    db: Session,
    ticket_in: schemas.TicketCreate,
    sentiment: str,
    confidence: float,
) -> models.Ticket:
    """Insert a row and return the populated ORM object."""
    ticket = models.Ticket(
        title=ticket_in.title,
        message=ticket_in.message,
        category=ticket_in.category,
        sentiment=sentiment,
        confidence=confidence,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> List[models.Ticket]:
    """Return tickets newest-first with simple limit/offset pagination."""
    stmt = (
        select(models.Ticket)
        .order_by(models.Ticket.created_at.desc(), models.Ticket.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all())
