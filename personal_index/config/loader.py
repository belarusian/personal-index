"""Configuration loader and saver."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml

from personal_index.config.models import (
    AppConfig,
    CrawlerConfig,
    IndexConfig,
    Interest,
    MatchMode,
    SchedulerConfig,
)

DEFAULT_CONFIG_FILENAME = "config.yaml"


def _parse_match_mode(value: str) -> MatchMode:
    """Parse match mode string."""
    try:
        return MatchMode(value.lower())
    except (ValueError, AttributeError):
        return MatchMode.ANY


def _parse_interest(data: Dict[str, Any]) -> Interest:
    """Parse interest from dictionary."""
    return Interest(
        name=data["name"],
        keywords=data.get("keywords", []),
        url_patterns=data.get("url_patterns", []),
        match_mode=_parse_match_mode(data.get("match_mode", "any")),
        priority=data.get("priority", 5),
        enabled=data.get("enabled", True),
    )


def load_config(config_path: str) -> AppConfig:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        return AppConfig()
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return AppConfig()

    interests = [_parse_interest(i) for i in data.get("interests", [])]

    crawler_data = data.get("crawler", {})
    crawler = CrawlerConfig(
        max_depth=crawler_data.get("max_depth", 3),
        politeness_delay=crawler_data.get("politeness_delay", 1.0),
        rate_limit=crawler_data.get("rate_limit", 10),
        timeout=crawler_data.get("timeout", 30),
        respect_robots_txt=crawler_data.get("respect_robots_txt", True),
    )

    scheduler_data = data.get("scheduler", {})
    scheduler = SchedulerConfig(
        enabled=scheduler_data.get("enabled", False),
        interval_hours=scheduler_data.get("interval_hours", 24),
    )

    index_data = data.get("index", {})
    index = IndexConfig(
        index_path=index_data.get("index_path", ".personal_index"),
        enable_stemming=index_data.get("enable_stemming", True),
    )

    return AppConfig(
        data_dir=data.get("data_dir", ".personal_index"),
        interests=interests,
        crawler=crawler,
        scheduler=scheduler,
        index=index,
    )


def save_config(config: AppConfig, config_path: str) -> None:
    """Save configuration to YAML file."""
    os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
    data = {
        "data_dir": config.data_dir,
        "interests": [
            {
                "name": i.name,
                "keywords": i.keywords,
                "url_patterns": i.url_patterns,
                "match_mode": i.match_mode.value,
                "priority": i.priority,
                "enabled": i.enabled,
            }
            for i in config.interests
        ],
        "crawler": {
            "max_depth": config.crawler.max_depth,
            "politeness_delay": config.crawler.politeness_delay,
            "rate_limit": config.crawler.rate_limit,
            "timeout": config.crawler.timeout,
            "respect_robots_txt": config.crawler.respect_robots_txt,
        },
        "scheduler": {
            "enabled": config.scheduler.enabled,
            "interval_hours": config.scheduler.interval_hours,
        },
        "index": {
            "index_path": config.index.index_path,
            "enable_stemming": config.index.enable_stemming,
        },
    }
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def create_default_config(config_path: str) -> str:
    """Create a default configuration file."""
    config = AppConfig()
    save_config(config, config_path)
    return config_path
