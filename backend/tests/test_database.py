"""Tests for safe database sessions and schema verification."""

import pytest

from app import database, main


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


def test_database_initialization_retries_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup survives temporary DNS or PostgreSQL failures."""

    attempts = 0
    delays: list[float] = []

    def create_schema(*, bind: object) -> None:
        nonlocal attempts
        assert bind is main.engine
        attempts += 1
        if attempts < 3:
            raise ConnectionError("temporary DNS failure")

    monkeypatch.setenv("DATABASE_STARTUP_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("DATABASE_STARTUP_RETRY_SECONDS", "0.25")
    monkeypatch.setattr(main.Base.metadata, "create_all", create_schema)
    monkeypatch.setattr(main.time, "sleep", delays.append)

    main.initialize_database()

    assert attempts == 3
    assert delays == [0.25, 0.25]


def test_database_initialization_raises_after_retry_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A persistent database failure eventually stops application startup."""

    def create_schema(*, bind: object) -> None:
        assert bind is main.engine
        raise ConnectionError("database unavailable")

    monkeypatch.setenv("DATABASE_STARTUP_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("DATABASE_STARTUP_RETRY_SECONDS", "0")
    monkeypatch.setattr(main.Base.metadata, "create_all", create_schema)
    monkeypatch.setattr(main.time, "sleep", lambda _delay: None)

    with pytest.raises(ConnectionError, match="database unavailable"):
        main.initialize_database()
