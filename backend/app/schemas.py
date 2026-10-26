"""Pydantic request and response schemas for task API operations."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class TaskStatus(str, Enum):
    """Allowed lifecycle states for an operational task."""

    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskCreate(BaseModel):
    """Validated fields accepted when creating a task."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)


class TaskUpdate(BaseModel):
    """Optional task fields accepted by partial updates."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)
    status: TaskStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def required_values_cannot_be_null(
        cls,
        value: str | TaskStatus | None,
        info: ValidationInfo,
    ) -> str | TaskStatus:
        """Reject explicit nulls for fields that are required when supplied."""

        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class TaskResponse(BaseModel):
    """Serialized task returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
