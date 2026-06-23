from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from mpxccp.models import Base


class ReadOnlySession(Session):
    def commit(self) -> None:
        raise InvalidRequestError("readonly session cannot commit")

    def flush(self, objects=None) -> None:
        raise InvalidRequestError("readonly session cannot flush")


def _sqlite_url(path: str | Path) -> str:
    if str(path) == ":memory:":
        return "sqlite:///:memory:"
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.resolve().as_posix()}"


def create_engine_for_path(path: str | Path) -> Engine:
    engine = create_engine(
        _sqlite_url(path),
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def readonly_session_scope(engine: Engine) -> Iterator[Session]:
    session = ReadOnlySession(engine, expire_on_commit=False, autoflush=False)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def init_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    from mpxccp.services.migration_service import MigrationService

    MigrationService(engine).run_all()
