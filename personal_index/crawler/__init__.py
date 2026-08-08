"""Web crawler module for Personal Index."""

from personal_index.crawler.crawler import WebCrawler
from personal_index.crawler.robots import RobotsChecker

# Re-export legacy crawler components for backward compatibility
from personal_index.crawler_legacy import (
    CrawledPage,
    RateLimiter,
    WebCrawler as LegacyWebCrawler,
)

__all__ = [
    "WebCrawler",
    "RobotsChecker",
    "CrawledPage",
    "RateLimiter",
    "LegacyWebCrawler",
]
