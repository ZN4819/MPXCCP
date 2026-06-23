from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from mpxccp.config.settings import (
    APP_NAME,
    DATABASE_FILENAME,
    EVIDENCE_ROOT_SETTING_KEY,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def development_data_path() -> Path:
    return project_root() / ".local_data" / DATABASE_FILENAME


def user_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def installed_data_path() -> Path:
    return user_data_dir() / DATABASE_FILENAME


def default_database_path() -> Path:
    if is_frozen():
        return installed_data_path()
    return development_data_path()


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", project_root()))
    return base.joinpath(*parts)


def resolve_evidence_root(setting_value: str, data_dir: Path | None = None) -> Path:
    evidence_root = Path(setting_value).expanduser()
    if evidence_root.is_absolute():
        return evidence_root
    return (data_dir or default_database_path().parent) / evidence_root


def evidence_root_from_settings(session: Session, data_dir: Path | None = None) -> Path:
    from mpxccp.models.shared import AppSetting

    setting_value = session.execute(
        select(AppSetting.value).where(AppSetting.key == EVIDENCE_ROOT_SETTING_KEY)
    ).scalar_one_or_none()
    if setting_value is None:
        raise KeyError(f"missing app setting: {EVIDENCE_ROOT_SETTING_KEY}")
    return resolve_evidence_root(setting_value, data_dir=data_dir)
