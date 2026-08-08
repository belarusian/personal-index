"""Content filtering — only store pages that match user interests."""

import fnmatch
import re
from urllib.parse import urlparse
from personal_index.models import Interest, IndexedPage


class ContentFilter:
    """Filters crawled content based on user-defined interests."""

    def __init__(self, interests: list[Interest]):
        self.interests = [i for i in interests if i.enabled]
        self._compiled_patterns = self._compile_url_patterns()

    def _compile_url_patterns(self) -> list[tuple[str, re.Pattern]]:
        """Compile URL glob patterns into regex patterns."""
        compiled = []
        for interest in self.interests:
            for pattern in interest.url_patterns:
                try:
                    regex = fnmatch.translate(pattern)
                    compiled.append((interest.name, re.compile(regex, re.IGNORECASE)))
                except re.error:
                    continue
        return compiled

    def matches_url(self, url: str) -> list[str]:
        """Check if a URL matches any interest's URL patterns.
        
        Returns list of matching interest names.
        """
        matched = []
        for interest_name, pattern in self._compiled_patterns:
            if pattern.match(url):
                matched.append(interest_name)
        return matched

    def matches_keywords(self, text: str, title: str = "") -> list[str]:
        """Check if text matches any interest's keywords.
        
        Returns list of matching interest names.
        """
        matched = []
        text_lower = text.lower()
        title_lower = title.lower()
        combined = f"{title_lower} {text_lower}"

        for interest in self.interests:
            for keyword in interest.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in combined:
                    if interest.name not in matched:
                        matched.append(interest.name)
                    break
        return matched

    def matches_topics(self, text: str, title: str = "") -> list[str]:
        """Check if text matches any interest's topics.
        
        Returns list of matching interest names.
        """
        matched = []
        text_lower = text.lower()
        title_lower = title.lower()
        combined = f"{title_lower} {text_lower}"

        for interest in self.interests:
            for topic in interest.topics:
                topic_lower = topic.lower()
                if topic_lower in combined:
                    if interest.name not in matched:
                        matched.append(interest.name)
                    break
        return matched

    def should_index(self, url: str, title: str = "", content: str = "") -> tuple[bool, list[str]]:
        """Determine if a page should be indexed based on interests.
        
        Returns (should_index, matched_interest_names).
        """
        matched = set()

        # Check URL patterns
        url_matches = self.matches_url(url)
        matched.update(url_matches)

        # Check keywords in content
        keyword_matches = self.matches_keywords(content, title)
        matched.update(keyword_matches)

        # Check topics in content
        topic_matches = self.matches_topics(content, title)
        matched.update(topic_matches)

        return (len(matched) > 0, list(matched))

    def filter_page(self, page: IndexedPage) -> tuple[bool, list[str]]:
        """Filter a single IndexedPage.
        
        Returns (should_keep, matched_interest_names).
        """
        return self.should_index(page.url, page.title, page.content)

    def filter_pages(self, pages: list[IndexedPage]) -> list[IndexedPage]:
        """Filter a list of pages, keeping only those matching interests.
        
        Updates matched_interests on each kept page.
        """
        kept = []
        for page in pages:
            should_keep, matched = self.filter_page(page)
            if should_keep:
                page.matched_interests = matched
                kept.append(page)
        return kept

    def get_all_keywords(self) -> list[str]:
        """Get all keywords from all interests."""
        keywords = []
        for interest in self.interests:
            keywords.extend(interest.keywords)
        return keywords

    def get_all_topics(self) -> list[str]:
        """Get all topics from all interests."""
        topics = []
        for interest in self.interests:
            topics.extend(interest.topics)
        return topics
