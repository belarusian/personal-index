"""Configuration loader - reads and writes YAML config files."""

import os
from pathlib import Path
from typing import Optional

import yaml

from personal_index.config.models import (
    AppConfig,
    CrawlerConfig,
    Interest,
    MatchMode,
    SchedulerConfig,
    IndexConfig,
)


DEFAULT_CONFIG_FILENAME = "personal_index.yaml"


def _parse_match_mode(value: str) -> MatchMode:
    """Parse match mode string to enum."""
    modes = {
        "any": MatchMode.ANY,
        "all": MatchMode.ALL,
        "regex": MatchMode.REGEX,
    }
    return modes.get(value.lower(), MatchMode.ANY)


def _parse_interest(data: dict) -> Interest:
    """Parse a dictionary into an Interest object."""
    return Interest(
        name=data["name"],
        keywords=data.get("keywords", []),
        url_patterns=data.get("url_patterns", []),
        match_mode=_parse_match_mode(data.get("match_mode", "any")),
        priority=data.get("priority", 5),
        enabled=data.get("enabled", True),
    )


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to config file. If None, searches for default.

    Returns:
        AppConfig with loaded values.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILENAME

    path = Path(config_path)
    if not path.exists():
        return AppConfig()

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if data is None:
        return AppConfig()

    # Parse interests
    interests = []
    for interest_data in data.get("interests", []):
        interests.append(_parse_interest(interest_data))

    # Parse crawler config
    crawler_data = data.get("crawler", {})
    crawler = CrawlerConfig(
        max_depth=crawler_data.get("max_depth", 3),
        max_pages_per_domain=crawler_data.get("max_pages_per_domain", 100),
        politeness_delay=crawler_data.get("politeness_delay", 1.0),
        rate_limit=crawler_data.get("rate_limit", 10),
        timeout=crawler_data.get("timeout", 30),
        user_agent=crawler_data.get("user_agent", "personal-index/0.1.0"),
        respect_robots_txt=crawler_data.get("respect_robots_txt", True),
        max_content_size=crawler_data.get("max_content_size", 1_000_000),
    )

    # Parse scheduler config
    scheduler_data = data.get("scheduler", {})
    scheduler = SchedulerConfig(
        enabled=scheduler_data.get("enabled", False),
        interval_hours=scheduler_data.get("interval_hours", 24),
        max_concurrent_crawls=scheduler_data.get("max_concurrent_crawls", 1),
        crawl_all_interests=scheduler_data.get("crawl_all_interests", True),
    )

    # Parse index config
    index_data = data.get("index", {})
    index = IndexConfig(
        index_path=index_data.get("index_path", ".personal_index"),
        min_term_freq=index_data.get("min_term_freq", 1),
        max_index_size_mb=index_data.get("max_index_size_mb", 500),
        enable_stemming=index_data.get("enable_stemming", True),
        enable_stop_words=index_data.get("enable_stop_words", True),
    )

    return AppConfig(
        data_dir=data.get("data_dir", ".personal_index"),
        interests=interests,
        crawler=crawler,
        scheduler=scheduler,
        index=index,
    )


def save_config(config: AppConfig, config_path: Optional[str] = None) -> str:
    """Save configuration to a YAML file.

    Args:
        config: AppConfig to save.
        config_path: Path to save to. Defaults to DEFAULT_CONFIG_FILENAME.

    Returns:
        Path where config was saved.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILENAME

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
            "max_pages_per_domain": config.crawler.max_pages_per_domain,
            "politeness_delay": config.crawler.politeness_delay,
            "rate_limit": config.crawler.rate_limit,
            "timeout": config.crawler.timeout,
            "user_agent": config.crawler.user_agent,
            "respect_robots_txt": config.crawler.respect_robots_txt,
            "max_content_size": config.crawler.max_content_size,
        },
        "scheduler": {
            "enabled": config.scheduler.enabled,
            "interval_hours": config.scheduler.interval_hours,
            "max_concurrent_crawls": config.scheduler.max_concurrent_crawls,
            "crawl_all_interests": config.scheduler.crawl_all_interests,
        },
        "index": {
            "index_path": config.index.index_path,
            "min_term_freq": config.index.min_term_freq,
            "max_index_size_mb": config.index.max_index_size_mb,
            "enable_stemming": config.index.enable_stemming,
            "enable_stop_words": config.index.enable_stop_words,
        },
    }

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return str(path)


def create_default_config(config_path: Optional[str] = None) -> str:
    """Create a default configuration file.

    Returns:
        Path to the created config file.
    """
    config = AppConfig()
    return save_config(config, config_path)
