"""URL classification for categorizing crawled URLs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLCategory(str, Enum):
    """URLCategory."""
    PAGE = "page"
    API = "api"
    MEDIA = "media"
    DOCUMENT = "document"
    FEED = "feed"
    REDIRECT = "redirect"
    ERROR = "error"
    STATIC = "static"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of URL classification."""

    url: str
    category: URLCategory
    confidence: float = 0.5
    reasons: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class URLClassifier:
    """Classifies URLs into categories based on patterns."""

    API_PATTERNS: ClassVar[list[str]] = [
        r"/api/",
        r"/v\d+/",
        r"\.json$",
        r"\.xml$",
        r"\.yaml$",
        r"/graphql",
        r"/rest/",
    ]

    MEDIA_PATTERNS: ClassVar[list[str]] = [
        r"\.(jpg|jpeg|png|gif|webp|svg|ico|bmp)$",
        r"\.(mp3|wav|ogg|flac|m4a)$",
        r"\.(mp4|avi|mov|wmv|webm|mkv)$",
        r"/images/",
        r"/media/",
        r"/static/",
        r"/assets/",
    ]

    DOCUMENT_PATTERNS: ClassVar[list[str]] = [
        r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|txt|rtf|odt)$",
        r"/docs/",
        r"/documents/",
        r"/files/",
        r"/downloads/",
    ]

    FEED_PATTERNS: ClassVar[list[str]] = [
        r"\.rss$",
        r"\.atom$",
        r"/feed",
        r"/rss",
        r"/atom",
        r"/sitemap",
    ]

    STATIC_PATTERNS: ClassVar[list[str]] = [
        r"\.(css|js|map)$",
        r"/static/",
        r"/assets/",
        r"/vendor/",
        r"/node_modules/",
    ]

    REDIRECT_PATTERNS: ClassVar[list[str]] = [
        r"/redirect",
        r"/goto",
        r"/redirect",
        r"\?url=",
        r"\?redirect=",
    ]

    def __init__(self):
        self._api_re = [re.compile(p, re.IGNORECASE) for p in self.API_PATTERNS]
        self._media_re = [re.compile(p, re.IGNORECASE) for p in self.MEDIA_PATTERNS]
        self._doc_re = [re.compile(p, re.IGNORECASE) for p in self.DOCUMENT_PATTERNS]
        self._feed_re = [re.compile(p, re.IGNORECASE) for p in self.FEED_PATTERNS]
        self._static_re = [re.compile(p, re.IGNORECASE) for p in self.STATIC_PATTERNS]
        self._redirect_re = [re.compile(p, re.IGNORECASE) for p in self.REDIRECT_PATTERNS]

    def _match_category(
        self,
        url: str,
        path: str,
        full_url: str,
        patterns: list[re.Pattern],
        category: URLCategory,
        confidence: float,
        reason: str,
    ) -> ClassificationResult | None:
        """Generic pattern match helper for URL classification.

        Args:
            url: Original URL string.
            path: Lowercased URL path.
            full_url: Lowercased full URL.
            patterns: Compiled regex patterns to match against.
            category: Category to assign if a match is found.
            confidence: Confidence score for the classification.
            reason: Reason string for the classification.

        Returns:
            ClassificationResult if a pattern matches, None otherwise.
        """
        for pattern in patterns:
            if pattern.search(full_url) or pattern.search(path):
                return ClassificationResult(
                    url=url,
                    category=category,
                    confidence=confidence,
                    reasons=[reason],
                )
        return None

    def classify(self, url: str) -> ClassificationResult:
        """Classify a URL into a category."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        full_url = url.lower()

        # Data-driven classification rules: (patterns, category, confidence, reason)
        rules = [
            (self._redirect_re, URLCategory.REDIRECT, 0.8, "matches redirect pattern"),
            (self._feed_re, URLCategory.FEED, 0.9, "matches feed pattern"),
            (self._api_re, URLCategory.API, 0.85, "matches API pattern"),
            (self._static_re, URLCategory.STATIC, 0.9, "matches static asset pattern"),
            (self._media_re, URLCategory.MEDIA, 0.85, "matches media pattern"),
            (self._doc_re, URLCategory.DOCUMENT, 0.85, "matches document pattern"),
        ]

        for patterns, category, confidence, reason in rules:
            result = self._match_category(
                url, path, full_url, patterns, category, confidence, reason,
            )
            if result:
                return result

        # Default to page
        return ClassificationResult(
            url=url, category=URLCategory.PAGE, confidence=0.5,
            reasons=["no specific pattern matched"],
        )

    def classify_batch(self, urls: list[str]) -> list[ClassificationResult]:
        """Classify multiple URLs."""
        return [self.classify(url) for url in urls]

    def get_category_counts(self, urls: list[str]) -> dict[str, int]:
        """Get count of URLs per category."""
        counts: dict[str, int] = {}
        for url in urls:
            result = self.classify(url)
            cat = result.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    @property
    def api_re(self):
        """Api_re."""
        return self._api_re

    @property
    def media_re(self):
        """Media_re."""
        return self._media_re

    @property
    def feed_re(self):
        """Feed_re."""
        return self._feed_re

    @property
    def static_re(self):
        """Static_re."""
        return self._static_re

    @property
    def redirect_re(self):
        """Redirect_re."""
        return self._redirect_re
