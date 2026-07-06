"""Database engine and request-session dependency."""

import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy.engine import URL, Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def get_database_url() -> URL:
    """Return an explicit URL or build PostgreSQL settings from the environment."""

    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return make_url(configured_url)

    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DATABASE_USER", "opstasks"),
        password=os.getenv("DATABASE_PASSWORD", "opstasks"),
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "opstasks"),
    )


database_url = get_database_url()
engine_options: dict[str, object] = {"pool_pre_ping": True}
if database_url.drivername.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine: Engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Provide one database session and always clean it up."""

    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
