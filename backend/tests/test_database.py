"""Tests for safe database sessions and schema verification."""

import pytest

from app import database


class RecordingSession:
    """Record cleanup operations performed by the request dependency."""

    def __init__(self) -> None:
        """Initialize operation flags."""

        self.rolled_back = False
        self.closed = False

    def rollback(self) -> None:
        """Record a transaction rollback."""

        self.rolled_back = True

    def close(self) -> None:
        """Record session closure."""

        self.closed = True


def test_engine_checks_connections_before_reuse() -> None:
    """The application engine rejects stale pooled PostgreSQL connections."""

    assert getattr(database.engine.pool, "_pre_ping") is True


def test_failed_request_rolls_back_and_closes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An endpoint failure cannot leave an invalid transaction in the pool."""

    session = RecordingSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(RuntimeError, match="operation failed"):
        dependency.throw(RuntimeError("operation failed"))

    assert session.rolled_back is True
    assert session.closed is True


def test_successful_request_closes_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful requests close their session without unnecessary rollback."""

    session = RecordingSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)

    assert session.rolled_back is False
    assert session.closed is True
