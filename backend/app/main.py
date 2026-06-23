"""FastAPI application entry point.

Phase 1: wires DB bootstrap (`create_all`) on startup and includes the
tickets router. Sentiment is still the stub from `routers/tickets`; the
real model is loaded in Phase 2.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import sentiment  # noqa: F401  (Phase 2: load_model() lives there)
from app.config import settings
from app.database import Base, engine
from app.routers import health, tickets

# Import models so that Base.metadata is populated before create_all runs.
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema bootstrap — hackathon shortcut per IMPLEMENTATION_PLAN §4.
    # If the project ever grows past the demo, the upgrade path is Alembic.
    Base.metadata.create_all(bind=engine)

    # Phase 2 will replace this no-op with the real model load.
    sentiment.load_model()

    yield


app = FastAPI(
    title="Ticket Analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS is a fallback path per Decision #4. With the default empty config,
# the middleware is a no-op and same-origin /api routing is the only path.
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(tickets.router)


@app.get("/")
def root() -> dict:
    return {"service": "ticket-analyzer", "phase": 1}
