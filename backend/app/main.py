import logging
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from .database import engine, get_db, SessionLocal
from .models import Base
from .routes import router, fault_mode

# ─── Logging JSON ─────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"opstasks-backend","message":"%(message)s"}'
)
logger = logging.getLogger("opstasks")

# ─── App ──────────────────────────────────────────────────────────
app = FastAPI(title="OpsTasks API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Prometheus metrics ───────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ─── Routes ───────────────────────────────────────────────────────
app.include_router(router, prefix="/api")

# ─── Health checks ────────────────────────────────────────────────
@app.get("/health/live")
def liveness():
    return {"status": "ok"}

@app.get("/health/ready")
def readiness():
    if fault_mode["current"] == "degraded":
        return {"status": "degraded", "fault": "degraded"}, 503
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"readiness_failed error={str(e)}")
        return {"status": "error", "detail": "database unreachable"}, 503

# ─── Startup ──────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    logger.info("opstasks_starting")
    Base.metadata.create_all(bind=engine)
    logger.info("opstasks_ready")
