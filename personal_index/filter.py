"""Content filtering module.

Filters crawled content based on user-defined interests, keywords, and URL patterns.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .config import Interest


@dataclass
class FilterResult:
    """Result of filtering content against interests."""

    matched: bool
    matching_interests: list[str]
    score: float
    matched_keywords: list[str]


class ContentFilter:
    """Filters content based on user interests."""

    def __init__(self, interests: list[Interest]):
        self.interests = [i for i in interests if i.enabled]
        self._compiled_patterns: list[tuple[str, re.Pattern]] = []
        for interest in self.interests:
            for pattern in interest.url_patterns:
                try:
                    self._compiled_patterns.append((interest.topic, re.compile(pattern)))
                except re.error:
                    continue

    def filter_url(self, url: str) -> FilterResult:
        """Check if a URL matches any interest patterns."""
        matched_topics = []
        for topic, pattern in self._compiled_patterns:
            if pattern.search(url):
                matched_topics.append(topic)
        return FilterResult(
            matched=bool(matched_topics),
            matching_interests=matched_topics,
            score=len(matched_topics),
            matched_keywords=[],
        )

    def filter_content(self, text: str, title: str = "") -> FilterResult:
        """Check if content text matches any interest keywords."""
        matched_topics = []
        matched_keywords = []
        text_lower = text.lower()
        title_lower = title.lower()
        combined = f"{title_lower} {text_lower}"

        for interest in self.interests:
            topic_matched = False
            for keyword in interest.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in combined:
                    topic_matched = True
                    matched_keywords.append(keyword)
            if topic_matched:
                matched_topics.append(interest.topic)

        score = len(matched_keywords) / max(len(self._all_keywords()), 1)
        return FilterResult(
            matched=bool(matched_topics),
            matching_interests=matched_topics,
            score=score,
            matched_keywords=matched_keywords,
        )

    def filter_page(self, url: str, text: str, title: str = "") -> FilterResult:
        """Filter a page by checking both URL patterns and content."""
        url_result = self.filter_url(url)
        content_result = self.filter_content(text, title)

        all_topics = list(set(url_result.matching_interests + content_result.matching_interests))
        all_keywords = list(set(url_result.matched_keywords + content_result.matched_keywords))
        combined_score = (url_result.score + content_result.score) / 2

        return FilterResult(
            matched=bool(all_topics),
            matching_interests=all_topics,
            score=combined_score,
            matched_keywords=all_keywords,
        )

    def _all_keywords(self) -> list[str]:
        """Get all keywords from all interests."""
        keywords = []
        for interest in self.interests:
            keywords.extend(interest.keywords)
        return keywords

    def should_crawl(self, url: str) -> bool:
        """Determine if a URL should be crawled based on interest patterns."""
        if not self._compiled_patterns:
            return True
        return self.filter_url(url).matched

    def extract_relevant_text(self, text: str, max_length: int = 5000) -> str:
        """Extract relevant text, trimming to max length."""
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space]
        return truncated
