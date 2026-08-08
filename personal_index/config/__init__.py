"""Configuration package."""
from personal_index.config.models import (
    AppConfig,
    CrawlerConfig,
    IndexConfig,
    Interest,
    MatchMode,
    SchedulerConfig,
)
from personal_index.config.loader import (
    DEFAULT_CONFIG_FILENAME,
    create_default_config,
    load_config,
    save_config,
)

__all__ = [
    "AppConfig",
    "CrawlerConfig",
    "IndexConfig",
    "Interest",
    "MatchMode",
    "SchedulerConfig",
    "DEFAULT_CONFIG_FILENAME",
    "create_default_config",
    "load_config",
    "save_config",
]
