"""Task CRUD routes and controlled application faults."""

import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

logger = logging.getLogger("opstasks")
router = APIRouter()

fault_mode: dict[str, str | None] = {"current": None}
ENABLE_DEMO_FAULTS = os.getenv("ENABLE_DEMO_FAULTS", "false").lower() == "true"


def get_slow_delay_seconds() -> float:
    """Return the configured non-negative delay, defaulting to three seconds."""

    try:
        return max(0.0, float(os.getenv("DEMO_SLOW_DELAY_SECONDS", "3")))
    except ValueError:
        return 3.0


def apply_task_fault() -> None:
    """Apply the active error or latency fault before task work."""

    if fault_mode["current"] == "errors":
        logger.error("Injected task error")
        raise HTTPException(status_code=500, detail="Injected demo error")
    if fault_mode["current"] == "slow":
        delay = get_slow_delay_seconds()
        logger.warning("Injected %.1f second task delay", delay)
        time.sleep(delay)


@router.get("/tasks", response_model=list[schemas.TaskResponse])
def list_tasks(db: Session = Depends(get_db)) -> list[models.Task]:
    """Return all tasks, newest first."""

    apply_task_fault()
    return db.query(models.Task).order_by(models.Task.created_at.desc()).all()


@router.post("/tasks", response_model=schemas.TaskResponse, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)) -> models.Task:
    """Create and return a task."""

    apply_task_fault()
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int,
    task: schemas.TaskUpdate,
    db: Session = Depends(get_db),
) -> models.Task:
    """Update the supplied fields of a task."""

    apply_task_fault()
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a task."""

    apply_task_fault()
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()


@router.post("/demo/faults/{mode}")
def set_fault(mode: str) -> dict[str, str | None]:
    """Activate or clear an application fault in the local demo environment."""

    if not ENABLE_DEMO_FAULTS:
        raise HTTPException(status_code=403, detail="Demo faults are disabled")
    if mode not in {"degraded", "errors", "slow", "clear"}:
        raise HTTPException(status_code=400, detail=f"Unknown fault mode: {mode}")
    fault_mode["current"] = None if mode == "clear" else mode
    logger.warning("Fault mode changed to %s", mode)
    return {"fault_mode": fault_mode["current"]}
