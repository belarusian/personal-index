"""Configuration management for personal-index."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


DEFAULT_DATA_DIR = os.path.expanduser("~/.personal-index")


@dataclass
class AppConfig:
    """Application configuration."""

    data_dir: str = DEFAULT_DATA_DIR
    max_concurrent_requests: int = 5
    default_crawl_delay: float = 1.0
    default_crawl_depth: int = 3
    default_max_pages: int = 100
    default_search_limit: int = 10
    respect_robots: bool = True
    log_level: str = "INFO"
    log_file: Optional[str] = None
    user_agent: str = "personal-index/0.1.0"
    request_timeout: int = 10
    max_content_length: int = 50000
    index_compression: bool = False
    auto_schedule_update: bool = True


class ConfigManager:
    """Manages application configuration with file persistence."""

    CONFIG_FILENAME = "config.json"

    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = data_dir or os.environ.get(
            "PERSONAL_INDEX_DATA_DIR", DEFAULT_DATA_DIR
        )
        self._config_path = Path(self._data_dir) / self.CONFIG_FILENAME
        self._config = self._load()

    def _load(self) -> AppConfig:
        """Load configuration from file."""
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text())
                return AppConfig(**{
                    k: v for k, v in data.items()
                    if k in AppConfig.__dataclass_fields__
                })
            except (json.JSONDecodeError, TypeError, ValueError):
                return AppConfig()
        return AppConfig()

    def _save(self) -> None:
        """Save configuration to file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(asdict(self._config), indent=2))

    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config

    @property
    def data_dir(self) -> str:
        """Get the data directory."""
        return self._config.data_dir

    def get(self, key: str, default=None):
        """Get a configuration value by key."""
        return getattr(self._config, key, default)

    def set(self, key: str, value) -> bool:
        """Set a configuration value by key."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self._save()
            return True
        return False

    def update(self, **kwargs) -> None:
        """Update multiple configuration values."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self._save()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = AppConfig(data_dir=self._data_dir)
        self._save()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return asdict(self._config)

    def export(self, path: str) -> None:
        """Export configuration to a file."""
        Path(path).write_text(json.dumps(asdict(self._config), indent=2))

    @classmethod
    def from_dict(cls, data: dict, data_dir: Optional[str] = None) -> ConfigManager:
        """Create a ConfigManager from a dictionary."""
        manager = cls(data_dir=data_dir)
        for key, value in data.items():
            if hasattr(manager._config, key):
                setattr(manager._config, key, value)
        manager._save()
        return manager
