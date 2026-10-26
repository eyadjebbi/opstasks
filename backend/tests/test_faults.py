"""Tests for allowlisted and repeatable controlled fault behavior."""

from collections.abc import Callable, Iterator
from typing import cast

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import routes, schemas


@pytest.fixture(autouse=True)
def reset_fault_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Restore healthy fault configuration around every test."""

    previous_mode = routes.fault_mode["current"]
    previous_enabled = routes.ENABLE_DEMO_FAULTS
    monkeypatch.setattr(routes, "ENABLE_DEMO_FAULTS", True)
    routes.fault_mode["current"] = None
    yield
    routes.fault_mode["current"] = previous_mode
    monkeypatch.setattr(routes, "ENABLE_DEMO_FAULTS", previous_enabled)


def task_operations() -> list[Callable[[Session], object]]:
    """Build representative invocations for every task route."""

    return [
        lambda db: routes.list_tasks(db),
        lambda db: routes.create_task(schemas.TaskCreate(title="Test"), db),
        lambda db: routes.update_task(
            1,
            schemas.TaskUpdate(status=schemas.TaskStatus.done),
            db,
        ),
        lambda db: routes.delete_task(1, db),
    ]


@pytest.mark.parametrize("operation", task_operations())
def test_error_fault_applies_to_every_task_operation(
    operation: Callable[[Session], object],
) -> None:
    """Every task route returns the controlled HTTP 500 before database access."""

    routes.fault_mode["current"] = "errors"
    unused_database = cast(Session, None)

    with pytest.raises(HTTPException) as exception:
        operation(unused_database)

    assert exception.value.status_code == 500
    assert exception.value.detail == "Injected demo error"


def test_slow_fault_uses_configured_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slow mode delays task work using the configured number of seconds."""

    observed_delays: list[float] = []
    routes.fault_mode["current"] = "slow"
    monkeypatch.setenv("DEMO_SLOW_DELAY_SECONDS", "1.25")
    monkeypatch.setattr(routes.time, "sleep", observed_delays.append)

    routes.apply_task_fault()

    assert observed_delays == [1.25]


def test_invalid_slow_delay_falls_back_to_three_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid configuration uses the documented delay instead of crashing."""

    observed_delays: list[float] = []
    routes.fault_mode["current"] = "slow"
    monkeypatch.setenv("DEMO_SLOW_DELAY_SECONDS", "invalid")
    monkeypatch.setattr(routes.time, "sleep", observed_delays.append)

    routes.apply_task_fault()

    assert observed_delays == [3.0]


def test_degraded_fault_does_not_change_task_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Degraded mode affects readiness only, leaving task logic unchanged."""

    routes.fault_mode["current"] = "degraded"
    sleep_called = False

    def record_sleep(_delay: float) -> None:
        """Record an unexpected latency injection."""

        nonlocal sleep_called
        sleep_called = True

    monkeypatch.setattr(routes.time, "sleep", record_sleep)
    routes.apply_task_fault()

    assert sleep_called is False


def test_clear_mode_is_idempotent() -> None:
    """Clearing an active or already-clear fault always returns healthy state."""

    routes.fault_mode["current"] = "errors"

    assert routes.set_fault("clear") == {"fault_mode": None}
    assert routes.set_fault("clear") == {"fault_mode": None}
    assert routes.fault_mode["current"] is None


def test_unknown_fault_mode_is_rejected() -> None:
    """The controller rejects modes outside the explicit allowlist."""

    with pytest.raises(HTTPException) as exception:
        routes.set_fault("arbitrary")

    assert exception.value.status_code == 400
