"""Database engine and request-session dependency."""

import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy.engine import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def get_database_url() -> URL:
    """Build the PostgreSQL connection URL from environment variables."""

    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DATABASE_USER", "opstasks"),
        password=os.getenv("DATABASE_PASSWORD", "opstasks"),
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "opstasks"),
    )


engine: Engine = create_engine(get_database_url(), pool_pre_ping=True)
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
