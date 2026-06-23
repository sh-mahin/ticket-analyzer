"""Pydantic request/response models.

Field shapes mirror IMPLEMENTATION_PLAN.md §5 and PRD §8.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Request ---

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=100)


# --- Response ---

class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    category: Optional[str] = None
    sentiment: str
    confidence: float
    created_at: datetime


class HealthOut(BaseModel):
    status: str = "ok"
    # Non-breaking superset of the contract — acts as the cheapest possible
    # "is the model loaded yet" canary for the demo.
    model_loaded: bool = False
