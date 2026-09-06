"""Content matching and interest filtering."""

from __future__ import annotations

import re

from personal_index.config.models import Interest, MatchMode


class ContentMatcher:
    """Matches content against a single interest."""

    def __init__(self, interest: Interest):
        self.interest = interest

    def matches_content(self, text: str) -> bool:
        """Check if content matches this interest's keywords."""
        if not self.interest.enabled or not text:
            return False
        if not self.interest.keywords:
            return False

        text_lower = text.lower()

        if self.interest.match_mode == MatchMode.ANY:
            return any(
                kw.lower() in text_lower for kw in self.interest.keywords
            )
        if self.interest.match_mode == MatchMode.ALL:
            return all(
                kw.lower() in text_lower for kw in self.interest.keywords
            )
        if self.interest.match_mode == MatchMode.REGEX:
            for kw in self.interest.keywords:
                try:
                    if re.search(kw, text, re.IGNORECASE):
                        return True
                except re.error:
                    continue
            return False
        return False

    def matches_url(self, url: str) -> bool:
        """Check if URL matches this interest's patterns."""
        if not self.interest.enabled or not url:
            return False
        for pattern in self.interest.url_patterns:
            try:
                if re.search(pattern, url):
                    return True
            except re.error:
                continue
        return False

    def relevance_score(self, text: str) -> float:
        """Calculate relevance score for content."""
        if not self.interest.enabled or not text:
            return 0.0
        text_lower = text.lower()
        total = 0.0
        if self.interest.match_mode == MatchMode.REGEX:
            # REGEX keywords are patterns, not literal substrings: count
            # actual regex matches so a matching REGEX interest scores > 0
            # (a literal substring count of the pattern string is always 0).
            for kw in self.interest.keywords:
                try:
                    total += len(re.findall(kw, text, re.IGNORECASE))
                except re.error:
                    continue
        else:
            for kw in self.interest.keywords:
                total += text_lower.count(kw.lower())
        num_kw = max(len(self.interest.keywords), 1)
        return min(
            total * self.interest.priority / num_kw,
            self.interest.priority
        )


class InterestFilter:
    """Filters content against multiple interests."""

    def __init__(self, interests: list[Interest]):
        self._matchers = [
            ContentMatcher(i) for i in interests if i.enabled
        ]

    def matches(self, text: str, url: str = "") -> Interest | None:
        """Find the best matching interest (highest score)."""
        best = None
        best_score = 0.0
        for matcher in self._matchers:
            content_match = matcher.matches_content(text)
            url_match = matcher.matches_url(url)
            if content_match or url_match:
                score = matcher.relevance_score(text)
                # For URL-only matches, use priority as score
                if url_match and not content_match:
                    score = max(score, matcher.interest.priority)
                if score > best_score:
                    best_score = score
                    best = matcher.interest
        return best

    def get_matching_interests(
        self, text: str, url: str = ""
    ) -> list[Interest]:
        """Get all matching interests sorted by score."""
        results = []
        for matcher in self._matchers:
            if matcher.matches_content(text) or matcher.matches_url(url):
                results.append(matcher.interest)
        results.sort(key=lambda i: i.priority, reverse=True)
        return results

    def should_index(self, text: str, url: str = "") -> bool:
        """Check if content should be indexed."""
        return self.matches(text, url) is not None

    def filter_content(self, text: str, url: str = "") -> dict | None:
        """Filter content and return details if matched."""
        match = self.matches(text, url)
        if match is None:
            return None
        return {
            "matched": True,
            "interest": match.name,
            "score": match.priority,
        }
