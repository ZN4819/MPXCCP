from __future__ import annotations

import logging
from pathlib import Path

from mpxccp.config.paths import user_data_dir


def configure_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path:
    target_dir = log_dir or user_data_dir() / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / "mpxccp.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_path
