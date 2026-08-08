"""Content filtering for personal-index.

Filters crawled content based on user-defined interests,
ensuring only relevant content is stored and indexed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from personal_index.models import CrawledPage, Interest


@dataclass
class FilterResult:
    """Result of filtering a page against interests."""

    page: CrawledPage
    passed: bool
    matched_interests: list[str] = field(default_factory=list)
    match_scores: dict[str, float] = field(default_factory=dict)
    reason: str = ""


class ContentFilter:
    """Filters crawled pages based on user interests."""

    def __init__(self, interests: list[Interest]):
        self.interests = [i for i in interests if i.enabled]
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for URL matching."""
        for interest in self.interests:
            patterns = []
            for url_pattern in interest.url_patterns:
                try:
                    # Convert simple patterns to regex
                    regex_pattern = url_pattern.replace(".", r"\.")
                    regex_pattern = regex_pattern.replace("*", ".*")
                    patterns.append(re.compile(regex_pattern, re.IGNORECASE))
                except re.error:
                    # If pattern is invalid regex, use simple substring match
                    patterns.append(re.compile(re.escape(url_pattern), re.IGNORECASE))
            self._compiled_patterns[interest.topic] = patterns

    def filter_page(self, page: CrawledPage) -> FilterResult:
        """Filter a single page against all interests.

        Returns a FilterResult indicating whether the page should be stored.
        """
        matched_interests = []
        match_scores = {}

        for interest in self.interests:
            score = self._score_page_against_interest(page, interest)
            if score > 0:
                matched_interests.append(interest.topic)
                match_scores[interest.topic] = score

        passed = len(matched_interests) > 0
        reason = self._build_reason(passed, matched_interests, match_scores)

        if passed:
            page.matched_interests = matched_interests

        return FilterResult(
            page=page,
            passed=passed,
            matched_interests=matched_interests,
            match_scores=match_scores,
            reason=reason,
        )

    def _score_page_against_interest(
        self, page: CrawledPage, interest: Interest
    ) -> float:
        """Score how well a page matches an interest.

        Returns a score between 0.0 and 1.0.
        """
        score = 0.0
        max_score = 0.0

        # URL pattern matching (highest weight)
        if interest.url_patterns:
            max_score += 0.4
            if self._url_matches(page.url, interest):
                score += 0.4

        # Title keyword matching (high weight)
        if interest.keywords:
            max_score += 0.3
            title_matches = sum(
                1 for kw in interest.keywords
                if kw.lower() in page.title.lower()
            )
            if title_matches > 0:
                score += min(0.3, title_matches * 0.15)

        # Content keyword matching (medium weight)
        if interest.keywords:
            max_score += 0.3
            content_lower = page.content.lower()
            content_matches = sum(
                1 for kw in interest.keywords
                if kw.lower() in content_lower
            )
            if content_matches > 0:
                score += min(0.3, content_matches * 0.1)

        return score

    def _url_matches(self, url: str, interest: Interest) -> bool:
        """Check if URL matches any of the interest's URL patterns."""
        patterns = self._compiled_patterns.get(interest.topic, [])
        for pattern in patterns:
            if pattern.search(url):
                return True
        return False

    def _build_reason(
        self,
        passed: bool,
        matched_interests: list[str],
        match_scores: dict[str, float],
    ) -> str:
        """Build a human-readable reason for the filter result."""
        if not passed:
            return "No matching interests found"
        parts = []
        for topic in matched_interests:
            score = match_scores.get(topic, 0)
            parts.append(f"{topic} (score: {score:.2f})")
        return "Matched: " + ", ".join(parts)

    def should_crawl_url(self, url: str) -> tuple[bool, list[str]]:
        """Pre-filter: should we even crawl this URL?

        Returns (should_crawl, matching_interests).
        """
        matched = []
        for interest in self.interests:
            if interest.url_patterns:
                if self._url_matches(url, interest):
                    matched.append(interest.topic)
            # Also check if URL contains keywords
            for keyword in interest.keywords:
                if keyword.lower() in url.lower():
                    matched.append(interest.topic)
                    break
        return len(matched) > 0, list(set(matched))
