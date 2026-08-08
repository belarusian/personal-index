"""Content filtering module to only store content matching user interests."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from personal_index.interests import Interest, InterestManager
from personal_index.index import Document


@dataclass
class FilterConfig:
    """Configuration for content filtering."""
    min_content_length: int = 100
    min_title_length: int = 3
    blocked_extensions: List[str] = field(default_factory=lambda: [
        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.mp4', '.mp3',
        '.exe', '.bin', '.tar', '.gz', '.rar', '.7z',
    ])
    blocked_content_types: List[str] = field(default_factory=lambda: [
        'image/', 'video/', 'audio/', 'application/',
    ])
    max_content_length: int = 1_000_000  # 1MB
    require_interest_match: bool = True


class ContentFilter:
    """Filters crawled content based on user interests and configuration."""

    def __init__(self, interest_manager: InterestManager, config: Optional[FilterConfig] = None):
        self.interest_manager = interest_manager
        self.config = config or FilterConfig()

    def should_filter(self, document: Document) -> bool:
        """Return True if document should be filtered out (not stored)."""
        if self._is_blocked_extension(document.url):
            return True

        if self._is_blocked_content_type(document.metadata.get('content_type', '')):
            return True

        if self._is_too_short(document):
            return True

        if self._is_too_long(document):
            return True

        if self.config.require_interest_match:
            if not self._matches_interests(document):
                return True

        return False

    def _is_blocked_extension(self, url: str) -> bool:
        """Check if URL has a blocked file extension."""
        url_lower = url.lower().split('?')[0]
        for ext in self.config.blocked_extensions:
            if url_lower.endswith(ext):
                return True
        return False

    def _is_blocked_content_type(self, content_type: str) -> bool:
        """Check if content type is blocked."""
        if not content_type:
            return False
        for blocked in self.config.blocked_content_types:
            if content_type.startswith(blocked):
                return True
        return False

    def _is_too_short(self, document: Document) -> bool:
        """Check if document content is too short."""
        if len(document.title) < self.config.min_title_length:
            return True
        if len(document.content) < self.config.min_content_length:
            return True
        return False

    def _is_too_long(self, document: Document) -> bool:
        """Check if document content is too long."""
        return len(document.content) > self.config.max_content_length

    def _matches_interests(self, document: Document) -> bool:
        """Check if document matches any user interest."""
        if not self.interest_manager.list_interests():
            return True  # No interests defined = accept all

        text = document.searchable_text
        matching = self.interest_manager.matches_any(text=text, url=document.url)
        return len(matching) > 0

    def get_matching_interests(self, document: Document) -> List[str]:
        """Return list of interest names that match the document."""
        text = document.searchable_text
        return self.interest_manager.matches_any(text=text, url=document.url)

    def filter_documents(self, documents: List[Document]) -> List[Document]:
        """Filter a list of documents, returning only those that pass."""
        return [doc for doc in documents if not self.should_filter(doc)]
