import logging
from pathlib import Path

from app.paths import get_log_dir


def configure_logging() -> Path:
    log_path = get_log_dir() / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_path
