"""
Content filtering for personal-index.

Filters crawled content based on user-defined interests,
keywords, topics, and URL patterns.
"""

import re
from dataclasses import dataclass
from typing import Optional
from personal_index.interests import InterestStore


@dataclass
class FilterResult:
    """Result of filtering content against interests."""
    matched: bool
    matching_interests: list[str] = None
    score: float = 0.0
    matched_keywords: list[str] = None
    matched_patterns: list[str] = None

    def __post_init__(self):
        if self.matching_interests is None:
            self.matching_interests = []
        if self.matched_keywords is None:
            self.matched_keywords = []
        if self.matched_patterns is None:
            self.matched_patterns = []


class ContentFilter:
    """Filters content based on user interests."""

    def __init__(self, interest_store: InterestStore):
        self._store = interest_store
        self._keyword_cache: Optional[set] = None
        self._pattern_cache: Optional[list] = None
        self._topic_cache: Optional[set] = None

    def _refresh_cache(self) -> None:
        """Refresh cached interest data."""
        self._keyword_cache = self._store.get_all_keywords()
        self._pattern_cache = self._store.get_all_url_patterns()
        self._topic_cache = self._store.get_all_topics()

    def filter_url(self, url: str) -> FilterResult:
        """Check if a URL matches any interest patterns."""
        if not self._pattern_cache:
            self._refresh_cache()

        matched_patterns = []
        for pattern in self._pattern_cache:
            if pattern.search(url):
                matched_patterns.append(pattern.pattern)

        if matched_patterns:
            return FilterResult(
                matched=True,
                matched_patterns=matched_patterns,
                score=len(matched_patterns) * 0.5,
            )
        return FilterResult(matched=False)

    def filter_content(self, text: str, url: str = "") -> FilterResult:
        """Check if content matches any interest keywords or topics."""
        if not self._keyword_cache:
            self._refresh_cache()

        text_lower = text.lower()
        matched_keywords = []
        matching_interests = []

        for interest in self._store.get_enabled():
            interest_match = False
            for keyword in interest.keywords:
                if keyword.lower() in text_lower:
                    matched_keywords.append(keyword)
                    interest_match = True
            for topic in interest.topics:
                if topic.lower() in text_lower:
                    interest_match = True
            if interest_match:
                matching_interests.append(interest.name)

        score = len(matched_keywords) * 0.3
        if matching_interests:
            score += len(matching_interests) * 0.2

        return FilterResult(
            matched=bool(matched_keywords or matching_interests),
            matching_interests=matching_interests,
            score=score,
            matched_keywords=matched_keywords,
        )

    def should_index(self, url: str, title: str = "", content: str = "") -> FilterResult:
        """
        Determine if a page should be indexed based on URL patterns,
        title, and content.
        """
        url_result = self.filter_url(url)
        content_text = f"{title} {content}"
        content_result = self.filter_content(content_text, url)

        if url_result.matched or content_result.matched:
            combined_interests = list(set(
                url_result.matching_interests + content_result.matching_interests
            ))
            return FilterResult(
                matched=True,
                matching_interests=combined_interests,
                score=url_result.score + content_result.score,
                matched_keywords=content_result.matched_keywords,
                matched_patterns=url_result.matched_patterns,
            )
        return FilterResult(matched=False)

    def get_score(self, text: str) -> float:
        """Get a relevance score for text against all interests."""
        result = self.filter_content(text)
        return result.score
