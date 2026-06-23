"""SQLAlchemy ORM models.

Ticket column shape mirrors IMPLEMENTATION_PLAN.md §4 exactly.
"""

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, func

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    sentiment = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    # Server default so the DB owns clock time. Stored naive UTC by the
    # driver; serialized as ISO-8601 in the Pydantic schema.
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    # GET /tickets always sorts by recency — the index is the cheapest
    # possible defense against a 10k-row demo list slowing down.
    __table_args__ = (
        Index("ix_tickets_created_at_desc", created_at.desc()),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"Ticket(id={self.id!r}, title={self.title!r}, "
            f"sentiment={self.sentiment!r}, confidence={self.confidence!r})"
        )
