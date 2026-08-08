"""Configuration management for personal-index.

Handles loading, saving, and validating application configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration."""

    data_dir: str = "~/.personal-index"
    default_crawl_depth: int = 2
    default_max_pages: int = 100
    default_rate_limit: float = 1.0
    default_timeout: int = 10
    default_user_agent: str = "personal-index/0.1.0"
    respect_robots: bool = True
    max_content_length: int = 1_000_000
    search_index_dir: Optional[str] = None
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.search_index_dir is None:
            self.search_index_dir = str(
                Path(self.data_dir).expanduser() / "index"
            )


class ConfigManager:
    """Manages application configuration."""

    DEFAULT_CONFIG_FILE = "~/.personal-index/config.json"

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(
            config_file or self.DEFAULT_CONFIG_FILE
        ).expanduser()
        self.config = self._load_config()

    def _load_config(self) -> AppConfig:
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return AppConfig(**data)
            except (json.JSONDecodeError, TypeError):
                return AppConfig()
        return AppConfig()

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(asdict(self.config), f, indent=2)

    def get(self, key: str, default=None):
        """Get a configuration value by key."""
        return getattr(self.config, key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value by key."""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
        else:
            raise AttributeError(f"Unknown config key: {key}")

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.config = AppConfig()
        self.save()

    def as_dict(self) -> dict:
        """Return configuration as a dictionary."""
        return asdict(self.config)
