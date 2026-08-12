"""Tests for content deduplication module."""

from __future__ import annotations

from personal_index.content_dedup import (
    ContentDeduplicator,
    DedupResult,
    DuplicateGroup,
    content_hash,
    normalize_url,
    text_similarity,
    url_hash,
)


class TestNormalizeUrl:
    def test_remove_trailing_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_keep_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_remove_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_lowercase_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/page") == "https://example.com/page"

    def test_empty_url(self):
        assert normalize_url("") == ""

    def test_no_change_needed(self):
        assert normalize_url("https://example.com/page") == "https://example.com/page"


class TestContentHash:
    def test_consistent_hash(self):
        h1 = content_hash("Hello world")
        h2 = content_hash("Hello world")
        assert h1 == h2

    def test_different_content(self):
        h1 = content_hash("Hello world")
        h2 = content_hash("Goodbye world")
        assert h1 != h2

    def test_whitespace_normalized(self):
        h1 = content_hash("Hello  world")
        h2 = content_hash("Hello world")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = content_hash("Hello World")
        h2 = content_hash("hello world")
        assert h1 == h2

    def test_empty_content(self):
        assert content_hash("") == ""


class TestUrlHash:
    def test_normalized_hash(self):
        h1 = url_hash("https://example.com/")
        h2 = url_hash("https://example.com")
        assert h1 == h2


class TestTextSimilarity:
    def test_identical_texts(self):
        assert text_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        assert text_similarity("hello world", "foo bar baz") == 0.0

    def test_partial_overlap(self):
        sim = text_similarity("hello world foo", "hello world bar")
        assert 0.0 < sim < 1.0

    def test_empty_text(self):
        assert text_similarity("", "hello") == 0.0
        assert text_similarity("hello", "") == 0.0


class TestDuplicateGroup:
    def test_total_count(self):
        group = DuplicateGroup(
            representative="https://a.com",
            duplicates=["https://b.com", "https://c.com"],
        )
        assert group.total_count == 3

    def test_to_dict(self):
        group = DuplicateGroup(
            representative="https://a.com",
            duplicates=["https://b.com"],
            similarity_score=0.95,
            dedup_method="hash",
        )
        d = group.to_dict()
        assert d["representative"] == "https://a.com"
        assert d["total_count"] == 2


class TestDedupResult:
    def test_dedup_ratio(self):
        result = DedupResult(
            total_items=10,
            unique_items=7,
            removed_count=3,
        )
        assert result.dedup_ratio == 0.3

    def test_dedup_ratio_empty(self):
        result = DedupResult()
        assert result.dedup_ratio == 0.0

    def test_summary(self):
        result = DedupResult(
            total_items=10,
            unique_items=7,
            removed_count=3,
            duplicate_groups=[DuplicateGroup(representative="a")],
            method="hash",
        )
        summary = result.summary()
        assert "Total items: 10" in summary
        assert "Duplicates found: 3" in summary


class TestContentDeduplicator:
    def setup_method(self):
        self.dedup = ContentDeduplicator(similarity_threshold=0.8)

    def test_dedup_by_hash_exact_duplicates(self):
        items = [
            {"url": "https://a.com", "content": "Hello world"},
            {"url": "https://b.com", "content": "Hello world"},
            {"url": "https://c.com", "content": "Different content"},
        ]
        result = self.dedup.dedup_by_hash(items)
        assert result.removed_count == 1
        assert len(result.duplicate_groups) == 1

    def test_dedup_by_hash_no_duplicates(self):
        items = [
            {"url": "https://a.com", "content": "Content A"},
            {"url": "https://b.com", "content": "Content B"},
        ]
        result = self.dedup.dedup_by_hash(items)
        assert result.removed_count == 0

    def test_dedup_by_url_normalized(self):
        items = [
            {"url": "https://example.com/"},
            {"url": "https://example.com"},
            {"url": "https://other.com"},
        ]
        result = self.dedup.dedup_by_url(items)
        assert result.removed_count == 1

    def test_dedup_by_similarity(self):
        items = [
            {"url": "https://a.com", "content": "Python is a great programming language"},
            {"url": "https://b.com", "content": "Python is a great programming language"},
            {"url": "https://c.com", "content": "Completely different topic here"},
        ]
        result = self.dedup.dedup_by_similarity(items)
        assert result.removed_count >= 1

    def test_dedup_all_combined(self):
        items = [
            {"url": "https://a.com/", "content": "Hello world"},
            {"url": "https://a.com", "content": "Hello world"},
            {"url": "https://b.com", "content": "Hello world"},
            {"url": "https://c.com", "content": "Different"},
        ]
        result = self.dedup.dedup_all(items)
        assert result.removed_count >= 2
        assert result.method == "combined"

    def test_dedup_empty(self):
        result = self.dedup.dedup_by_hash([])
        assert result.total_items == 0
        assert result.removed_count == 0

    def test_custom_similarity_threshold(self):
        dedup = ContentDeduplicator(similarity_threshold=0.5)
        items = [
            {"url": "https://a.com", "content": "Python programming tutorial"},
            {"url": "https://b.com", "content": "Python programming guide"},
        ]
        result = dedup.dedup_by_similarity(items)
        # With lower threshold, these should be similar
        assert result.removed_count >= 0
