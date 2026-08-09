"""Content deduplication - detect duplicate saved content."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SimilarityMethod(str, Enum):
    """Available similarity detection methods."""

    HASH = "hash"
    TFIDF = "tfidf"
    JACCARD = "jaccard"


@dataclass
class DuplicateGroup:
    """A group of duplicate content items."""

    representative: str
    duplicates: list[str] = field(default_factory=list)
    similarity_score: float = 0.0

    @property
    def total_count(self) -> int:
        """Total items in this group (representative + duplicates)."""
        return 1 + len(self.duplicates)


@dataclass
class DedupResult:
    """Result of deduplication analysis."""

    total_items: int = 0
    unique_items: int = 0
    duplicate_groups: int = 0
    groups: list[DuplicateGroup] = field(default_factory=list)

    @property
    def duplicate_ratio(self) -> float:
        """Ratio of duplicate items to total items."""
        if self.total_items == 0:
            return 0.0
        return (self.total_items - self.unique_items) / self.total_items


@dataclass
class AddItemResult:
    """Result of adding an item to the deduplicator."""

    is_duplicate: bool = False
    original_url: Optional[str] = None
    similarity_score: float = 0.0


@dataclass
class DedupConfig:
    """Configuration for content deduplication."""

    similarity_threshold: float = 0.85
    method: str = "hash"
    min_content_length: int = 50

    _VALID_METHODS = {"hash", "tfidf", "jaccard"}

    def __post_init__(self) -> None:
        if self.method not in self._VALID_METHODS:
            raise ValueError(
                f"Invalid method '{self.method}'. Must be one of: {self._VALID_METHODS}"
            )


class ContentDeduplicator:
    """Detect duplicate or near-duplicate saved content.

    Supports hash-based exact matching, Jaccard similarity, and TF-IDF
    cosine similarity for flexible duplicate detection.
    """

    def __init__(self, config: Optional[DedupConfig] = None) -> None:
        self.config = config or DedupConfig()
        self._content_hashes: dict[str, str] = {}  # hash -> first url
        self._content_tokens: dict[str, set[str]] = {}  # url -> token set
        self._content_texts: dict[str, str] = {}  # url -> text
        self._content_tfidf: dict[str, dict[str, float]] = {}  # url -> tfidf vector
        self._idf_cache: dict[str, float] = {}  # term -> idf

    def find_duplicates(self, items: list[dict[str, Any]]) -> DedupResult:
        """Find duplicate groups among content items.

        Args:
            items: List of dicts with 'url', 'title', 'content' keys.

        Returns:
            DedupResult with duplicate groups and statistics.
        """
        # Filter items by minimum content length
        valid_items = [
            item for item in items
            if len(item.get("content", "")) >= self.config.min_content_length
        ]

        if not valid_items:
            return DedupResult(total_items=len(items), unique_items=len(items))

        groups: dict[str, DuplicateGroup] = {}

        if self.config.method == "hash":
            groups = self._find_hash_duplicates(valid_items)
        elif self.config.method == "jaccard":
            groups = self._find_jaccard_duplicates(valid_items)
        elif self.config.method == "tfidf":
            groups = self._find_tfidf_duplicates(valid_items)

        # Calculate unique items
        duplicate_urls: set[str] = set()
        for group in groups.values():
            duplicate_urls.update(group.duplicates)

        unique_items = len(valid_items) - len(duplicate_urls)

        return DedupResult(
            total_items=len(items),
            unique_items=max(unique_items, len(valid_items) - len(duplicate_urls)),
            duplicate_groups=len(groups),
            groups=list(groups.values()),
        )

    def add_items(self, items: list[dict[str, Any]]) -> AddItemResult:
        """Add items incrementally and check for duplicates.

        Args:
            items: List of content item dicts.

        Returns:
            AddItemResult for the first item (indicating if it's a duplicate).
        """
        results: list[AddItemResult] = []
        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            title = item.get("title", "")

            if len(content) < self.config.min_content_length:
                results.append(AddItemResult())
                continue

            result = self._check_single_item(url, title, content)
            results.append(result)

            if not result.is_duplicate:
                self._register_item(url, content)

        return results[0] if results else AddItemResult()

    def get_unique_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Get unique items, removing duplicates.

        Args:
            items: List of content item dicts.

        Returns:
            List of unique items (first occurrence kept).
        """
        seen_hashes: set[str] = set()
        unique: list[dict[str, Any]] = []

        for item in items:
            content = item.get("content", "")
            if len(content) < self.config.min_content_length:
                unique.append(item)
                continue

            content_hash = self._compute_hash(content)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(item)

        return unique

    def clear(self) -> None:
        """Clear all stored state."""
        self._content_hashes.clear()
        self._content_tokens.clear()
        self._content_texts.clear()
        self._content_tfidf.clear()
        self._idf_cache.clear()

    def _check_single_item(
        self, url: str, title: str, content: str
    ) -> AddItemResult:
        """Check a single item against stored content."""
        content_hash = self._compute_hash(content)

        if content_hash in self._content_hashes:
            original = self._content_hashes[content_hash]
            return AddItemResult(
                is_duplicate=True,
                original_url=original,
                similarity_score=1.0,
            )

        # Check similarity for non-hash methods
        if self.config.method in ("jaccard", "tfidf"):
            tokens = self._tokenize(content)
            for stored_url, stored_tokens in self._content_tokens.items():
                if stored_url == url:
                    continue
                if self.config.method == "jaccard":
                    score = self._jaccard_similarity(tokens, stored_tokens)
                else:
                    score = self._cosine_similarity(
                        self._compute_tfidf(tokens),
                        self._content_tfidf.get(stored_url, {}),
                    )
                if score >= self.config.similarity_threshold:
                    return AddItemResult(
                        is_duplicate=True,
                        original_url=stored_url,
                        similarity_score=score,
                    )

        return AddItemResult()

    def _register_item(self, url: str, content: str) -> None:
        """Register an item in the deduplicator."""
        content_hash = self._compute_hash(content)
        self._content_hashes[content_hash] = url
        tokens = self._tokenize(content)
        self._content_tokens[url] = tokens
        self._content_texts[url] = content
        self._content_tfidf[url] = self._compute_tfidf(tokens)

    def _find_hash_duplicates(
        self, items: list[dict[str, Any]]
    ) -> dict[str, DuplicateGroup]:
        """Find exact duplicates using content hashing."""
        groups: dict[str, DuplicateGroup] = {}
        seen: dict[str, str] = {}  # hash -> representative url

        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            content_hash = self._compute_hash(content)

            if content_hash in seen:
                rep_url = seen[content_hash]
                if rep_url in groups:
                    groups[rep_url].duplicates.append(url)
                else:
                    groups[rep_url] = DuplicateGroup(
                        representative=rep_url,
                        duplicates=[url],
                        similarity_score=1.0,
                    )
            else:
                seen[content_hash] = url

        return groups

    def _find_jaccard_duplicates(
        self, items: list[dict[str, Any]]
    ) -> dict[str, DuplicateGroup]:
        """Find near-duplicates using Jaccard similarity."""
        groups: dict[str, DuplicateGroup] = {}
        assigned: set[str] = set()
        token_sets: dict[str, set[str]] = {}

        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            tokens = self._tokenize(content)
            token_sets[url] = tokens

        for i, item_a in enumerate(items):
            url_a = item_a.get("url", "")
            if url_a in assigned:
                continue

            tokens_a = token_sets[url_a]
            group = DuplicateGroup(representative=url_a, similarity_score=1.0)

            for j, item_b in enumerate(items):
                if i >= j:
                    continue
                url_b = item_b.get("url", "")
                if url_b in assigned:
                    continue

                tokens_b = token_sets[url_b]
                score = self._jaccard_similarity(tokens_a, tokens_b)

                if score >= self.config.similarity_threshold:
                    group.duplicates.append(url_b)
                    group.similarity_score = max(
                        group.similarity_score, score
                    )
                    assigned.add(url_b)

            if group.duplicates:
                groups[url_a] = group

        return groups

    def _find_tfidf_duplicates(
        self, items: list[dict[str, Any]]
    ) -> dict[str, DuplicateGroup]:
        """Find near-duplicates using TF-IDF cosine similarity."""
        groups: dict[str, DuplicateGroup] = {}
        assigned: set[str] = set()
        tfidf_vectors: dict[str, dict[str, float]] = {}

        # Compute IDF across all items
        all_tokens: list[set[str]] = []
        for item in items:
            content = item.get("content", "")
            tokens = self._tokenize(content)
            all_tokens.append(tokens)

        N = len(all_tokens)
        if N == 0:
            return groups

        # Compute IDF
        doc_freq: Counter = Counter()
        for tokens in all_tokens:
            doc_freq.update(tokens)

        idf: dict[str, float] = {}
        for term, df in doc_freq.items():
            idf[term] = math.log((N + 1) / (df + 1)) + 1

        # Compute TF-IDF vectors
        for idx, item in enumerate(items):
            url = item.get("url", "")
            tokens = all_tokens[idx]
            tfidf_vectors[url] = self._compute_tfidf_with_idf(tokens, idf)

        # Compare vectors
        for i, item_a in enumerate(items):
            url_a = item_a.get("url", "")
            if url_a in assigned:
                continue

            vec_a = tfidf_vectors[url_a]
            group = DuplicateGroup(representative=url_a, similarity_score=1.0)

            for j, item_b in enumerate(items):
                if i >= j:
                    continue
                url_b = item_b.get("url", "")
                if url_b in assigned:
                    continue

                vec_b = tfidf_vectors[url_b]
                score = self._cosine_similarity(vec_a, vec_b)

                if score >= self.config.similarity_threshold:
                    group.duplicates.append(url_b)
                    group.similarity_score = max(group.similarity_score, score)
                    assigned.add(url_b)

            if group.duplicates:
                groups[url_a] = group

        return groups

    def _compute_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into a set of lowercase words."""
        return set(re.findall(r"\b[a-z0-9]{2,}\b", text.lower()))

    def _jaccard_similarity(self, set_a: set[str], set_b: set[str]) -> float:
        """Compute Jaccard similarity between two token sets."""
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _compute_tfidf(self, tokens: set[str]) -> dict[str, float]:
        """Compute simple TF vector for tokens."""
        counter = Counter(list(tokens))
        total = sum(counter.values())
        if total == 0:
            return {}
        return {term: count / total for term, count in counter.items()}

    def _compute_tfidf_with_idf(
        self, tokens: set[str], idf: dict[str, float]
    ) -> dict[str, float]:
        """Compute TF-IDF vector with precomputed IDF."""
        counter = Counter(list(tokens))
        total = sum(counter.values())
        if total == 0:
            return {}
        vector: dict[str, float] = {}
        for term, count in counter.items():
            tf = count / total
            vector[term] = tf * idf.get(term, 1.0)
        return vector

    def _cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two sparse vectors."""
        if not vec_a or not vec_b:
            return 0.0

        # Find common terms
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        if not common_terms:
            return 0.0

        dot_product = sum(vec_a[t] * vec_b[t] for t in common_terms)

        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)
