from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from app.constants import APP_NAME


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative_path


def get_app_data_dir() -> Path:
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    path = get_app_data_dir() / "config.json"
    if not path.exists():
        default_config = resource_path("config/default_config.json")
        shutil.copyfile(default_config, path)
    return path


def get_database_path(config_database_path: str | None = None) -> Path:
    if config_database_path:
        configured = Path(config_database_path)
        if configured.is_absolute():
            configured.parent.mkdir(parents=True, exist_ok=True)
            return configured
    path = get_app_data_dir() / "recorder.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_export_dir() -> Path:
    path = get_app_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path
