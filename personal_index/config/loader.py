"""Configuration loader for personal-index."""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml

from personal_index.config.models import AppConfig, Interest, MatchMode

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILENAME = "config.yaml"


def _parse_match_mode(value: str) -> MatchMode:
    """Parse a match mode string into a MatchMode enum."""
    value_lower = value.lower() if isinstance(value, str) else "any"
    try:
        return MatchMode(value_lower)
    except ValueError:
        return MatchMode.ANY


def _parse_interest(data: dict) -> Interest:
    """Parse an interest dictionary into an Interest object."""
    match_mode = data.get("match_mode", "any")
    if isinstance(match_mode, str):
        match_mode = _parse_match_mode(match_mode)
    elif not isinstance(match_mode, MatchMode):
        match_mode = MatchMode.ANY

    return Interest(
        name=data.get("name", ""),
        keywords=data.get("keywords", []),
        url_patterns=data.get("url_patterns", []),
        topics=data.get("topics", []),
        priority=data.get("priority", 5),
        enabled=data.get("enabled", True),
        match_mode=match_mode,
    )


def load_config(path: str) -> AppConfig:
    """Load configuration from a YAML file."""
    if not os.path.exists(path):
        logger.info("Config file not found: %s, using defaults", path)
        return AppConfig()

    try:
        with open(path) as f:
            data: dict | None = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error("Failed to parse config: %s", e)
        return AppConfig()

    if data is None:
        data = {}

    if not isinstance(data, dict):
        logger.error("Config file %s is not a mapping, using defaults", path)
        return AppConfig()

    return AppConfig(
        data_dir=data.get("data_dir", ".personal_index"),
        crawler=_parse_crawler(data),
        index=_parse_index(data),
        scheduler=_parse_scheduler(data),
        interests=_parse_interests(data),
        log_level=data.get("log_level", "INFO"),
    )


def _parse_interests(data: dict) -> list[Interest]:
    """Parse interests from config data."""
    interests = []
    for item in data.get("interests", []):
        if isinstance(item, dict):
            interests.append(_parse_interest(item))
    return interests


def _parse_crawler(data: dict) -> Any:
    """Parse crawler config section."""
    from personal_index.config.models import CrawlerConfig
    crawler_data = data.get("crawler", data.get("crawl", {}))
    return CrawlerConfig(**crawler_data) if crawler_data else CrawlerConfig()


def _parse_index(data: dict) -> Any:
    """Parse index config section."""
    from personal_index.config.models import IndexConfig
    index_data = data.get("index", {})
    return IndexConfig(**index_data) if index_data else IndexConfig()


def _parse_scheduler(data: dict) -> Any:
    """Parse scheduler config section."""
    from personal_index.config.models import SchedulerConfig
    scheduler_data = data.get("scheduler", {})
    return SchedulerConfig(**scheduler_data) if scheduler_data else SchedulerConfig()


def save_config(config: AppConfig, path: str) -> None:
    """Save configuration to a YAML file.

    Args:
        config: AppConfig instance to save.
        path: Path to write the YAML file.
    """
    data = config.to_dict()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    logger.info("Config saved to %s", path)


def validate_config(config: AppConfig) -> list[str]:
    """Validate configuration and return list of errors."""
    return config.validate()


def get_default_config() -> AppConfig:
    """Return a default AppConfig instance."""
    return AppConfig()


def create_default_config(path: str) -> str:
    """Create a default config file at the given path.

    Args:
        path: Path to create the config file.

    Returns:
        The path to the created file.
    """
    default = {
        "data_dir": ".personal_index",
        "crawler": {
            "max_depth": 3,
            "politeness_delay": 1.0,
            "rate_limit": 10,
            "respect_robots_txt": True,
            "timeout": 30,
        },
        "scheduler": {
            "enabled": False,
            "interval_hours": 24,
        },
        "index": {
            "enable_stemming": True,
            "index_path": ".personal_index",
        },
        "interests": [],
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(default, f, default_flow_style=False, sort_keys=False)
    return path


def merge_configs(base: AppConfig, override: dict) -> AppConfig:
    """Merge an override dict into a base config."""
    base_dict = base.to_dict()
    _deep_merge(base_dict, override)
    return AppConfig.from_dict(base_dict)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
