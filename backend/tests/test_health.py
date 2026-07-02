"""Focused tests for process health and controlled-fault safety."""

import json
from typing import NoReturn

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app import main, routes


def test_liveness_is_independent_of_dependencies() -> None:
    """Liveness reports a running process without checking PostgreSQL."""

    assert main.liveness() == {"status": "ok"}


def test_degraded_fault_returns_real_503() -> None:
    """The degraded mode must remove the backend from Kubernetes traffic."""

    previous_mode = routes.fault_mode["current"]
    routes.fault_mode["current"] = "degraded"
    try:
        response = main.readiness()
    finally:
        routes.fault_mode["current"] = previous_mode

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "fault": "degraded",
    }


def test_database_failure_returns_safe_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed database connection produces a generic readiness failure."""

    def unavailable_session() -> NoReturn:
        """Simulate PostgreSQL being unavailable before a session is opened."""

        raise ConnectionError("postgresql://user:secret@postgres/opstasks")

    monkeypatch.setattr(main, "SessionLocal", unavailable_session)
    response = main.readiness()

    assert isinstance(response, JSONResponse)
    body = json.loads(response.body)

    assert response.status_code == 503
    assert body == {"status": "error", "detail": "database unreachable"}
    assert "secret" not in response.body.decode()


def test_fault_endpoint_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fault injection requires explicit development configuration."""

    monkeypatch.setattr(routes, "ENABLE_DEMO_FAULTS", False)

    with pytest.raises(HTTPException) as exception:
        routes.set_fault("degraded")

    assert exception.value.status_code == 403
