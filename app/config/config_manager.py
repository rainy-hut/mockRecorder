from __future__ import annotations

import json
from pathlib import Path

from app.models import AppConfig
from app.paths import get_config_path


class ConfigManager:
    def __init__(self, path: Path | None = None):
        self.path = path or get_config_path()

    def load(self) -> AppConfig:
        with self.path.open("r", encoding="utf-8") as f:
            return AppConfig.from_dict(json.load(f))

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

    def import_json(self, path: str | Path) -> AppConfig:
        with Path(path).open("r", encoding="utf-8") as f:
            config = AppConfig.from_dict(json.load(f))
        self.save(config)
        return config

    def export_json(self, path: str | Path, config: AppConfig) -> None:
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
