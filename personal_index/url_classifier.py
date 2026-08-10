"""URL classification for categorizing crawled URLs."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
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

    API_PATTERNS = [
        r"/api/",
        r"/v\d+/",
        r"\.json$",
        r"\.xml$",
        r"\.yaml$",
        r"/graphql",
        r"/rest/",
    ]

    MEDIA_PATTERNS = [
        r"\.(jpg|jpeg|png|gif|webp|svg|ico|bmp)$",
        r"\.(mp3|wav|ogg|flac|m4a)$",
        r"\.(mp4|avi|mov|wmv|webm|mkv)$",
        r"/images/",
        r"/media/",
        r"/static/",
        r"/assets/",
    ]

    DOCUMENT_PATTERNS = [
        r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|txt|rtf|odt)$",
        r"/docs/",
        r"/documents/",
        r"/files/",
        r"/downloads/",
    ]

    FEED_PATTERNS = [
        r"\.rss$",
        r"\.atom$",
        r"/feed",
        r"/rss",
        r"/atom",
        r"/sitemap",
    ]

    STATIC_PATTERNS = [
        r"\.(css|js|map)$",
        r"/static/",
        r"/assets/",
        r"/vendor/",
        r"/node_modules/",
    ]

    REDIRECT_PATTERNS = [
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

    def classify(self, url: str) -> ClassificationResult:
        """Classify a URL into a category."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        full_url = url.lower()

        # Check redirects first
        for pattern in self.redirect_re:
            if pattern.search(full_url):
                return ClassificationResult(
                    url=url, category=URLCategory.REDIRECT, confidence=0.8,
                    reasons=["matches redirect pattern"],
                )

        # Check feeds
        for pattern in self.feed_re:
            if pattern.search(path):
                return ClassificationResult(
                    url=url, category=URLCategory.FEED, confidence=0.9,
                    reasons=["matches feed pattern"],
                )

        # Check API
        for pattern in self._api_re:
            if pattern.search(path):
                return ClassificationResult(
                    url=url, category=URLCategory.API, confidence=0.85,
                    reasons=["matches API pattern"],
                )

        # Check static assets
        for pattern in self._static_re:
            if pattern.search(path):
                return ClassificationResult(
                    url=url, category=URLCategory.STATIC, confidence=0.9,
                    reasons=["matches static asset pattern"],
                )

        # Check media
        for pattern in self._media_re:
            if pattern.search(path):
                return ClassificationResult(
                    url=url, category=URLCategory.MEDIA, confidence=0.85,
                    reasons=["matches media pattern"],
                )

        # Check documents
        for pattern in self._doc_re:
            if pattern.search(path):
                return ClassificationResult(
                    url=url, category=URLCategory.DOCUMENT, confidence=0.85,
                    reasons=["matches document pattern"],
                )

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
