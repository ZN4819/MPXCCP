from __future__ import annotations

APP_NAME = "MPXCCP"
APP_ORGANIZATION = "Codex"
DATABASE_FILENAME = "mpxccp.sqlite3"
EVIDENCE_ROOT_SETTING_KEY = "evidence_root"

DEFAULT_APP_SETTINGS: dict[str, str] = {
    EVIDENCE_ROOT_SETTING_KEY: "evidence",
}
