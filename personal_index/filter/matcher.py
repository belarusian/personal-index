"""Content matching and filtering logic."""

import re
from typing import Optional

from personal_index.config.models import Interest, MatchMode


class ContentMatcher:
    """Matches content against interest criteria."""

    def __init__(self, interest: Interest):
        """Initialize matcher with an interest.

        Args:
            interest: The interest to match against.
        """
        self.interest = interest
        self._compiled_patterns: list[re.Pattern] = []
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile URL patterns for performance."""
        self._compiled_patterns = []
        for pattern in self.interest.url_patterns:
            try:
                self._compiled_patterns.append(re.compile(pattern))
            except re.error:
                # Skip invalid patterns
                continue

    def matches_content(self, content: str) -> bool:
        """Check if content matches this interest.

        Args:
            content: Text content to check.

        Returns:
            True if content matches the interest criteria.
        """
        if not self.interest.enabled:
            return False

        if not self.interest.keywords:
            return False

        content_lower = content.lower()
        keywords_lower = [k.lower() for k in self.interest.keywords]

        if self.interest.match_mode == MatchMode.ANY:
            return any(kw in content_lower for kw in keywords_lower)
        elif self.interest.match_mode == MatchMode.ALL:
            return all(kw in content_lower for kw in keywords_lower)
        elif self.interest.match_mode == MatchMode.REGEX:
            for kw in keywords_lower:
                try:
                    if re.search(kw, content_lower):
                        return True
                except re.error:
                    continue
            return False

        return False

    def matches_url(self, url: str) -> bool:
        """Check if a URL matches this interest's patterns.

        Args:
            url: URL to check.

        Returns:
            True if URL matches any of the interest's patterns.
        """
        if not self.interest.enabled:
            return False

        if not self._compiled_patterns:
            return False

        return any(p.search(url) for p in self._compiled_patterns)

    def relevance_score(self, content: str) -> float:
        """Calculate relevance score for content against this interest.

        Higher score = more relevant.

        Args:
            content: Text content to score.

        Returns:
            Relevance score (0.0 to 10.0).
        """
        if not self.interest.enabled or not self.interest.keywords:
            return 0.0

        content_lower = content.lower()
        keywords_lower = [k.lower() for k in self.interest.keywords]

        # Count keyword occurrences
        total_matches = 0
        for kw in keywords_lower:
            total_matches += content_lower.count(kw)

        # Normalize and weight by priority
        if not total_matches:
            return 0.0

        # Score based on match density and priority
        density = min(total_matches / max(len(content_lower.split()), 1) * 100, 1.0)
        score = density * self.interest.priority

        return round(min(score, 10.0), 2)


class InterestFilter:
    """Filters content against multiple interests."""

    def __init__(self, interests: list[Interest]):
        """Initialize with a list of interests.

        Args:
            interests: List of interests to filter against.
        """
        self.interests = interests
        self._matchers: list[ContentMatcher] = [
            ContentMatcher(i) for i in interests if i.enabled
        ]

    def matches(self, content: str, url: str = "") -> Optional[Interest]:
        """Find the best matching interest for content.

        Args:
            content: Text content to match.
            url: Optional URL for pattern matching.

        Returns:
            Best matching Interest or None.
        """
        best_match: Optional[Interest] = None
        best_score = 0.0

        for matcher in self._matchers:
            if matcher.matches_content(content) or matcher.matches_url(url):
                score = matcher.relevance_score(content)
                if score > best_score:
                    best_score = score
                    best_match = matcher.interest

        return best_match

    def get_matching_interests(self, content: str, url: str = "") -> list[Interest]:
        """Get all interests that match the content.

        Args:
            content: Text content to match.
            url: Optional URL for pattern matching.

        Returns:
            List of matching interests sorted by relevance.
        """
        results = []
        for matcher in self._matchers:
            if matcher.matches_content(content) or matcher.matches_url(url):
                results.append((matcher.interest, matcher.relevance_score(content)))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]

    def should_index(self, content: str, url: str = "") -> bool:
        """Check if content should be indexed based on interests.

        Args:
            content: Text content to check.
            url: Optional URL.

        Returns:
            True if content matches at least one interest.
        """
        return self.matches(content, url) is not None

    def filter_content(self, content: str, url: str = "") -> Optional[dict]:
        """Filter content and return match details if it should be indexed.

        Args:
            content: Text content to filter.
            url: Optional URL.

        Returns:
            Dict with match details or None if no match.
        """
        matching = self.get_matching_interests(content, url)
        if not matching:
            return None

        best = matching[0]
        matcher = ContentMatcher(best)
        return {
            "matched": True,
            "interest": best.name,
            "relevance": matcher.relevance_score(content),
            "matching_interests": [i.name for i in matching],
        }
