"""Content filtering logic for Personal Index.

This module determines whether crawled content matches user-defined interests
and computes relevance scores for filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from personal_index.config import Interest
from personal_index.models import Page
from personal_index.utils import compute_relevance_score, tokenize


@dataclass
class FilterResult:
    """Result of filtering a page against interests."""

    passed: bool
    matched_interests: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)


class ContentFilter:
    """Filters crawled content based on user-defined interests."""

    def __init__(
        self,
        interests: list[Interest],
        min_relevance_score: float = 0.5,
        min_keyword_matches: int = 1,
    ) -> None:
        """Initialize the content filter.

        Args:
            interests: List of user-defined interests.
            min_relevance_score: Minimum relevance score to pass filter.
            min_keyword_matches: Minimum number of keyword matches required.
        """
        self.interests = interests
        self.min_relevance_score = min_relevance_score
        self.min_keyword_matches = min_keyword_matches

    def filter_page(self, page: Page) -> FilterResult:
        """Filter a single page against all interests.

        Args:
            page: The page to filter.

        Returns:
            FilterResult indicating whether the page passes.
        """
        all_matched_interests: list[str] = []
        all_matched_keywords: list[str] = []
        best_score = 0.0

        for interest in self.interests:
            if not interest.enabled:
                continue

            result = self._check_interest(page, interest)
            if result.passed:
                all_matched_interests.append(interest.topic)
                all_matched_keywords.extend(result.matched_keywords)
                best_score = max(best_score, result.relevance_score)

        # If no interests defined, pass all pages through
        if not self.interests:
            passed = True
        else:
            passed = (
                len(all_matched_interests) > 0
                and best_score >= self.min_relevance_score
                and len(all_matched_keywords) >= self.min_keyword_matches
            )

        return FilterResult(
            passed=passed,
            matched_interests=all_matched_interests,
            relevance_score=best_score,
            matched_keywords=list(set(all_matched_keywords)),
        )

    def _check_interest(self, page: Page, interest: Interest) -> FilterResult:
        """Check if a page matches a single interest.

        Args:
            page: The page to check.
            interest: The interest to check against.

        Returns:
            FilterResult for this interest.
        """
        text = page.content + " " + page.title + " " + page.meta_description
        matched_keywords: list[str] = []
        score = 0.0

        # Check URL patterns
        url_match = self._check_url_patterns(page.url, interest.url_patterns)

        # Check keywords
        keywords = interest.keywords
        if keywords:
            score = compute_relevance_score(
                text, keywords, title=page.title, priority=interest.priority
            )
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    matched_keywords.append(keyword)

        passed = (
            (url_match or len(matched_keywords) >= self.min_keyword_matches)
            and score >= self.min_relevance_score
        )

        return FilterResult(
            passed=passed,
            matched_interests=[interest.topic] if passed else [],
            relevance_score=score,
            matched_keywords=matched_keywords,
        )

    def _check_url_patterns(self, url: str, patterns: list[str]) -> bool:
        """Check if a URL matches any of the given patterns.

        Args:
            url: The URL to check.
            patterns: List of URL patterns (supports simple wildcards).

        Returns:
            True if URL matches any pattern.
        """
        for pattern in patterns:
            if self._url_matches_pattern(url, pattern):
                return True
        return False

    @staticmethod
    def _url_matches_pattern(url: str, pattern: str) -> bool:
        """Check if URL matches a pattern with wildcard support.

        Supports:
            - * matches any characters
            - ? matches single character

        Args:
            url: The URL to check.
            pattern: The pattern to match against.

        Returns:
            True if URL matches the pattern.
        """
        # Convert pattern to regex
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r"\*", ".*").replace(r"\?", ".")
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, url, re.IGNORECASE))

    def filter_url_pre_crawl(self, url: str) -> bool:
        """Pre-filter a URL before crawling based on URL patterns.

        Args:
            url: The URL to pre-filter.

        Returns:
            True if the URL should be crawled.
        """
        for interest in self.interests:
            if not interest.enabled:
                continue
            if self._check_url_patterns(url, interest.url_patterns):
                return True
        return False

    def update_page(self, page: Page, result: FilterResult) -> None:
        """Update a page with filter results.

        Args:
            page: The page to update.
            result: The filter result to apply.
        """
        page.matched_interests = result.matched_interests
        page.relevance_score = result.relevance_score
