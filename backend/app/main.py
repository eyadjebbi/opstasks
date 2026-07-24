"""FastAPI entry point for the task and fault-testing service."""

import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .database import SessionLocal, engine
from .models import Base
from .routes import fault_mode, router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opstasks")


def initialize_database() -> None:
    """Create the schema, retrying while PostgreSQL or cluster DNS starts."""

    attempts = int(os.getenv("DATABASE_STARTUP_MAX_ATTEMPTS", "30"))
    delay_seconds = float(os.getenv("DATABASE_STARTUP_RETRY_SECONDS", "2"))

    for attempt in range(1, attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exception:
            if attempt == attempts:
                logger.exception(
                    "Database initialization failed after %s attempts",
                    attempts,
                )
                raise
            logger.warning(
                "Database unavailable during startup (%s); retrying in %s seconds "
                "[attempt %s/%s]",
                type(exception).__name__,
                delay_seconds,
                attempt,
                attempts,
            )
            time.sleep(delay_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create the fixed demo schema and close connections on shutdown."""

    initialize_database()
    logger.info("OpsTasks backend ready")
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="OpsTasks API", lifespan=lifespan)
app.include_router(router, prefix="/api")


@app.get("/health/live")
def liveness() -> dict[str, str]:
    """Report whether the backend process can answer requests."""

    return {"status": "ok"}


@app.get("/health/ready", response_model=None)
def readiness() -> dict[str, str] | JSONResponse:
    """Report whether the backend and PostgreSQL can serve traffic."""

    if fault_mode["current"] == "degraded":
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "fault": "degraded"},
        )
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exception:
        logger.warning("Database unavailable: %s", type(exception).__name__)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "database unreachable"},
        )
