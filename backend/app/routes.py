import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import get_db

logger = logging.getLogger("opstasks")
router = APIRouter()

# ─── Fault state ──────────────────────────────────────────────────
fault_mode = {"current": None}
ENABLE_DEMO_FAULTS = os.getenv("ENABLE_DEMO_FAULTS", "true").lower() == "true"

# ─── Tasks CRUD ───────────────────────────────────────────────────
@router.get("/tasks", response_model=List[schemas.TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    if fault_mode["current"] == "errors":
        logger.error("task_list_failed fault_mode=errors message=Injected demo error")
        raise HTTPException(status_code=500, detail="Injected demo error")
    tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).all()
    logger.info(f"task_list count={len(tasks)}")
    return tasks

@router.post("/tasks", response_model=schemas.TaskResponse, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    logger.info(f"task_created id={db_task.id} title={db_task.title}")
    return db_task

@router.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)
    db.commit()
    db.refresh(db_task)
    logger.info(f"task_updated id={task_id}")
    return db_task

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    logger.info(f"task_deleted id={task_id}")

# ─── Demo faults ──────────────────────────────────────────────────
ALLOWED_FAULTS = ["degraded", "errors", "slow", "clear"]

@router.post("/demo/faults/{mode}")
def set_fault(mode: str):
    if not ENABLE_DEMO_FAULTS:
        raise HTTPException(status_code=403, detail="Demo faults are disabled")
    if mode not in ALLOWED_FAULTS:
        raise HTTPException(status_code=400, detail=f"Unknown fault mode: {mode}")
    fault_mode["current"] = None if mode == "clear" else mode
    logger.warning(f"fault_mode_set mode={mode}")
    return {"fault_mode": fault_mode["current"]}
