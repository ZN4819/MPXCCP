from __future__ import annotations

from pathlib import Path

from mpxccp.config.paths import resource_path

_REQUIRED_RESOURCES = (
    "styles/app.qss",
    "icons/app.png",
)


def resources_base_path() -> Path:
    return resource_path("mpxccp", "resources")


def required_resources() -> list[str]:
    return list(_REQUIRED_RESOURCES)


def validate_resources(base_path: str | Path | None = None) -> list[str]:
    root = Path(base_path) if base_path is not None else resources_base_path()
    return [
        relative_path
        for relative_path in _REQUIRED_RESOURCES
        if not (root / relative_path).is_file()
    ]
