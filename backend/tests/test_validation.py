"""Tests for strict and normalized task API validation."""

import pytest
from pydantic import ValidationError

from app import schemas


def test_create_trims_title_and_description() -> None:
    """Surrounding whitespace is removed before values reach the database."""

    task = schemas.TaskCreate(
        title="  Inspect logs  ",
        description="  Review recent errors  ",
    )

    assert task.title == "Inspect logs"
    assert task.description == "Review recent errors"


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_create_rejects_invalid_titles(title: str) -> None:
    """Titles must contain between one and 120 meaningful characters."""

    with pytest.raises(ValidationError):
        schemas.TaskCreate(title=title)


def test_create_rejects_description_over_limit() -> None:
    """Descriptions cannot exceed the documented 1,000-character limit."""

    with pytest.raises(ValidationError):
        schemas.TaskCreate(title="Valid", description="x" * 1001)


@pytest.mark.parametrize("payload", [{"title": None}, {"status": None}])
def test_update_rejects_null_required_values(payload: dict[str, object]) -> None:
    """Explicit null cannot erase a required title or task status."""

    with pytest.raises(ValidationError):
        schemas.TaskUpdate.model_validate(payload)


def test_update_rejects_unknown_status() -> None:
    """Only the three documented lifecycle states are accepted."""

    with pytest.raises(ValidationError):
        schemas.TaskUpdate.model_validate({"status": "blocked"})
