from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select, text

import mpxccp.models as models
from mpxccp.repositories.session import create_engine_for_path, init_database, session_scope
from mpxccp.services.migration_service import MigrationService
from mpxccp.services.scoring_service import ScoringService


def _engine(tmp_path: Path):
    engine = create_engine_for_path(tmp_path / "task16-migrations.sqlite3")
    init_database(engine)
    return engine


def test_migrations_are_idempotent_and_keep_single_indicator_set(tmp_path):
    engine = _engine(tmp_path)

    MigrationService(engine).run_all()
    MigrationService(engine).run_all()

    assert ScoringService(engine).count_indicators() == 41
    with session_scope(engine) as session:
        migration_count = session.scalar(select(func.count()).select_from(models.DataVersion))
        names = session.execute(select(models.DataVersion.migration_name)).scalars().all()

    assert len(names) == len(set(names))
    assert migration_count >= 9


def test_migration_failure_logs_warning_and_continues_next_migration(tmp_path, caplog):
    engine = _engine(tmp_path)
    service = MigrationService(engine)

    def fail_cleanup(session):
        raise RuntimeError("legacy cleanup failed")

    def good_followup(session):
        session.execute(text("select 1"))

    caplog.set_level("WARNING", logger="mpxccp.services.migration_service")
    service.run_migrations(
        (
            ("broken_cleanup", "1", "Broken noncritical cleanup.", fail_cleanup),
            ("good_followup", "1", "Follow-up migration.", good_followup),
        )
    )

    assert "broken_cleanup" in caplog.text
    with session_scope(engine) as session:
        assert session.scalar(
            select(models.DataVersion).where(models.DataVersion.migration_name == "broken_cleanup")
        ) is None
        assert session.scalar(
            select(models.DataVersion).where(models.DataVersion.migration_name == "good_followup")
        ) is not None

