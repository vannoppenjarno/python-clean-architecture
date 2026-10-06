"""Infrastructure layer: database engine creation and schema setup."""

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

import hotel.infrastructure.tables  # noqa: F401  (registers the tables on SQLModel.metadata)

_IN_MEMORY_SQLITE_URLS = {"sqlite://", "sqlite:///:memory:"}


def create_db_engine(url: str) -> Engine:
    if url in _IN_MEMORY_SQLITE_URLS:
        # Every new connection to an in-memory SQLite database gets an empty database,
        # so share a single connection across all sessions and threads.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    if url.startswith("sqlite"):
        # FastAPI runs sync endpoints in a thread pool.
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


def create_tables(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
