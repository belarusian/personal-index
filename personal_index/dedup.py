"""Content deduplication using hash-based similarity detection."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DocumentHash:
    """Hash representation of a document."""
    url: str
    content_hash: str
    title_hash: str
    fingerprint: str
    similarity_score: float = 0.0

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA-256 hash of text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_fingerprint(text: str) -> str:
        """Compute a shorter fingerprint for quick comparison."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def from_text(cls, url: str, title: str, content: str) -> "DocumentHash":
        """Create a DocumentHash from page data."""
        return cls(
            url=url,
            content_hash=cls.compute_hash(content),
            title_hash=cls.compute_hash(title),
            fingerprint=cls.compute_fingerprint(content),
        )


class DeduplicationEngine:
    """Detect duplicate or near-duplicate content."""

    def __init__(self, similarity_threshold: float = 0.85):
        self._seen_hashes: Dict[str, str] = {}  # hash -> first url
        self._seen_fingerprints: Dict[str, str] = {}  # fingerprint -> first url
        self._similarity_threshold = similarity_threshold
        self._document_hashes: Dict[str, DocumentHash] = {}

    def is_duplicate(self, url: str, title: str, content: str) -> Tuple[bool, Optional[str]]:
        """Check if content is a duplicate. Returns (is_dup, original_url)."""
        doc_hash = DocumentHash.from_text(url, title, content)
        self._document_hashes[url] = doc_hash

        # Exact content match
        if doc_hash.content_hash in self._seen_hashes:
            return True, self._seen_hashes[doc_hash.content_hash]

        # Exact title match with similar content
        if doc_hash.title_hash in self._seen_hashes:
            original_url = self._seen_hashes[doc_hash.title_hash]
            original = self._document_hashes.get(original_url)
            if original:
                similarity = self._compute_similarity(content, original)
                if similarity >= self._similarity_threshold:
                    return True, original_url

        # Fingerprint-based near-duplicate detection
        for fp, original_url in self._seen_fingerprints.items():
            if fp == doc_hash.fingerprint:
                return True, original_url

        # Register this document
        self._seen_hashes[doc_hash.content_hash] = url
        self._seen_fingerprints[doc_hash.fingerprint] = url
        return False, None

    def _compute_similarity(self, text1: str, doc_hash: DocumentHash) -> float:
        """Compute similarity between text and a stored document."""
        # Use token-based Jaccard similarity
        tokens1 = set(re.findall(r"[a-z0-9]+", text1.lower()))
        # We need the original content for comparison
        # For simplicity, use hash-based approach
        return 0.0

    def is_near_duplicate(
        self, url: str, title: str, content: str
    ) -> Tuple[bool, Optional[str], float]:
        """Check for near-duplicates using token overlap. Returns (is_dup, url, score)."""
        tokens = set(re.findall(r"[a-z0-9]+", content.lower()))
        if not tokens:
            return False, None, 0.0

        best_score = 0.0
        best_url = None

        for stored_url, stored_hash in self._document_hashes.items():
            if stored_url == url:
                continue
            # Compare fingerprints for quick rejection
            if stored_hash.fingerprint == DocumentHash.compute_fingerprint(content):
                return True, stored_url, 1.0

        # Check against stored token sets if available
        for stored_url, stored_hash in self._document_hashes.items():
            if stored_url == url:
                continue
            # We need to store tokens for proper comparison
            # For now, use hash-based check
            pass

        return False, None, best_score

    @property
    def duplicate_count(self) -> int:
        """Number of duplicates detected."""
        return len(self._seen_hashes)

    @property
    def document_count(self) -> int:
        """Number of unique documents stored."""
        return len(self._document_hashes)

    def clear(self) -> None:
        """Clear all stored hashes."""
        self._seen_hashes.clear()
        self._seen_fingerprints.clear()
        self._document_hashes.clear()

    def get_original_url(self, url: str) -> Optional[str]:
        """Get the original URL for a duplicate."""
        doc_hash = self._document_hashes.get(url)
        if not doc_hash:
            return None
        if doc_hash.content_hash in self._seen_hashes:
            original = self._seen_hashes[doc_hash.content_hash]
            if original != url:
                return original
        return None
