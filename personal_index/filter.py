"""Content filtering module for matching pages against user interests."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from personal_index.config import Interest
from personal_index.content import ExtractedContent, tokenize


@dataclass
class FilterResult:
    """Result of filtering content against interests."""

    url: str
    passed: bool
    matched_interests: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    reasons: List[str] = field(default_factory=list)


class ContentFilter:
    """Filters web content based on user-defined interests."""

    def __init__(self, interests: List[Interest] = None):
        self.interests = interests or []
        self._keyword_index: Dict[str, List[str]] = {}
        self._build_keyword_index()

    def _build_keyword_index(self) -> None:
        """Build an inverted index of keywords to interest topics."""
        self._keyword_index = {}
        for interest in self.interests:
            if not interest.enabled:
                continue
            for keyword in interest.keywords:
                kw_lower = keyword.lower()
                if kw_lower not in self._keyword_index:
                    self._keyword_index[kw_lower] = []
                self._keyword_index[kw_lower].append(interest.topic)
            # Also index the topic itself
            topic_lower = interest.topic.lower()
            if topic_lower not in self._keyword_index:
                self._keyword_index[topic_lower] = []
            self._keyword_index[topic_lower].append(interest.topic)

    def add_interest(self, interest: Interest) -> None:
        """Add an interest to the filter."""
        self.interests.append(interest)
        self._build_keyword_index()

    def remove_interest(self, topic: str) -> bool:
        """Remove an interest by topic name."""
        for i, interest in enumerate(self.interests):
            if interest.topic == topic:
                self.interests.pop(i)
                self._build_keyword_index()
                return True
        return False

    def filter_content(self, content: ExtractedContent) -> FilterResult:
        """Filter a single piece of content against all interests."""
        result = FilterResult(url=content.url, passed=False)

        searchable_text = content.get_searchable_text().lower()
        tokens = set(tokenize(searchable_text))

        matched_topics = set()
        matched_kws = set()

        for interest in self.interests:
            if not interest.enabled:
                continue

            # Check keyword matches
            for keyword in interest.keywords:
                kw_lower = keyword.lower()
                if kw_lower in searchable_text or kw_lower in tokens:
                    matched_topics.add(interest.topic)
                    matched_kws.add(keyword)

            # Check topic match
            if interest.topic.lower() in searchable_text:
                matched_topics.add(interest.topic)

            # Check URL pattern matches
            for pattern in interest.url_patterns:
                if self._url_matches_pattern(content.url, pattern):
                    matched_topics.add(interest.topic)

        result.matched_interests = list(matched_topics)
        result.matched_keywords = list(matched_kws)
        result.passed = len(matched_topics) > 0

        # Calculate relevance score
        result.relevance_score = self._calculate_relevance(
            matched_topics, matched_kws, interest
        )

        # Build reasons
        if result.passed:
            result.reasons = [
                f"Matched interests: {', '.join(result.matched_interests)}",
                f"Matched keywords: {', '.join(result.matched_keywords)}",
            ]
        else:
            result.reasons = ["No matching interests found"]

        return result

    def filter_batch(self, contents: List[ExtractedContent]) -> List[FilterResult]:
        """Filter multiple content items."""
        return [self.filter_content(c) for c in contents]

    def get_matching_interests(self, text: str) -> List[Interest]:
        """Get all interests that match a given text."""
        text_lower = text.lower()
        tokens = set(tokenize(text_lower))
        matching = []
        for interest in self.interests:
            if not interest.enabled:
                continue
            if interest.matches(text):
                matching.append(interest)
        return matching

    def _url_matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches a pattern with wildcards."""
        regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".") + "$"
        return bool(re.match(regex_pattern, url, re.IGNORECASE))

    def _calculate_relevance(
        self,
        matched_topics: Set[str],
        matched_keywords: Set[str],
        interest: Optional[Interest] = None,
    ) -> float:
        """Calculate relevance score for matched content."""
        score = 0.0

        # Base score from number of matched interests
        score += len(matched_topics) * 10

        # Bonus for keyword matches
        score += len(matched_keywords) * 5

        # Priority boost from matched interests
        for topic in matched_topics:
            for interest in self.interests:
                if interest.topic == topic:
                    score += interest.priority

        return round(score, 2)

    def get_stats(self) -> dict:
        """Get filter statistics."""
        return {
            "total_interests": len(self.interests),
            "enabled_interests": sum(1 for i in self.interests if i.enabled),
            "indexed_keywords": len(self._keyword_index),
        }
