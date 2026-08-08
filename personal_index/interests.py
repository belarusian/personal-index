"""Interest configuration module for defining topics, keywords, and URL patterns."""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Interest:
    """Represents a single interest to track."""
    name: str
    keywords: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    def matches_text(self, text: str) -> bool:
        """Check if text matches any of the interest's keywords."""
        if not self.keywords:
            return True
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def matches_url(self, url: str) -> bool:
        """Check if URL matches any of the interest's URL patterns."""
        if not self.url_patterns:
            return True
        url_lower = url.lower()
        for pattern in self.url_patterns:
            if re.search(pattern, url_lower):
                return True
        return False


class InterestManager:
    """Manages a collection of user interests."""

    def __init__(self):
        self.interests: List[Interest] = []

    def add_interest(self, interest: Interest) -> None:
        """Add a new interest."""
        if any(i.name == interest.name for i in self.interests):
            raise ValueError(f"Interest '{interest.name}' already exists")
        self.interests.append(interest)

    def remove_interest(self, name: str) -> None:
        """Remove an interest by name."""
        self.interests = [i for i in self.interests if i.name != name]

    def get_interest(self, name: str) -> Optional[Interest]:
        """Get an interest by name."""
        for interest in self.interests:
            if interest.name == name:
                return interest
        return None

    def list_interests(self) -> List[Interest]:
        """List all interests."""
        return list(self.interests)

    def matches_any(self, text: str = "", url: str = "") -> List[str]:
        """Return names of interests that match the given text or URL."""
        matching = []
        for interest in self.interests:
            if interest.matches_text(text) and interest.matches_url(url):
                matching.append(interest.name)
        return matching
