"""CLI module for Personal Index."""

from personal_index.cli.main import cli as main
from personal_index.cli.main import interest as interests
from personal_index.cli.main import crawl
from personal_index.cli.main import search
from personal_index.cli.main import status
from personal_index.cli.main import stats

# Also expose the old-style CLI commands for backward compatibility
from personal_index.cli_legacy import (
    main as legacy_main,
    interests as legacy_interests,
    crawl as legacy_crawl,
    search as legacy_search,
    index as legacy_index,
    schedule as legacy_schedule,
    config as legacy_config,
)

# Re-export old-style names for test compatibility
index = legacy_index
schedule = legacy_schedule
config = legacy_config

__all__ = [
    "main",
    "interests",
    "crawl",
    "search",
    "status",
    "stats",
    "index",
    "schedule",
    "config",
    "legacy_main",
    "legacy_interests",
    "legacy_crawl",
    "legacy_search",
    "legacy_index",
    "legacy_schedule",
    "legacy_config",
]
