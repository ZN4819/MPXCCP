from __future__ import annotations

import sys
from pathlib import Path

from mpxccp.config.paths import resource_path

_REQUIRED_RESOURCES = (
    "styles/app.qss",
    "icons/app.png",
    "templates/.keep",
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


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    base_path = args[0] if args else None
    missing = validate_resources(base_path)
    if missing:
        print("missing required resources:")
        for relative_path in missing:
            print(f"- {relative_path}")
        return 1
    print("resource check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
