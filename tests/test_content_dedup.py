"""Tests for content deduplication module."""

from __future__ import annotations

import pytest

from personal_index.content_dedup import (
    AddItemResult,
    BatchDedupReport,
    ContentDeduplicator,
    DedupConfig,
    DedupResult,
    DeduplicationEngine,
    DocumentHash,
    DuplicateGroup,
    SimilarityMethod,
    find_duplicates,
    remove_duplicates,
)


class TestDocumentHash:
    """Tests for DocumentHash class."""

    def test_compute_hash_deterministic(self):
        h1 = DocumentHash.compute_hash("hello world")
        h2 = DocumentHash.compute_hash("hello world")
        assert h1 == h2

    def test_compute_hash_different(self):
        h1 = DocumentHash.compute_hash("hello")
        h2 = DocumentHash.compute_hash("world")
        assert h1 != h2

    def test_compute_fingerprint_deterministic(self):
        f1 = DocumentHash.compute_fingerprint("hello world")
        f2 = DocumentHash.compute_fingerprint("hello world")
        assert f1 == f2

    def test_fingerprint_length(self):
        fp = DocumentHash.compute_fingerprint("test content")
        assert len(fp) == 16

    def test_from_text(self):
        dh = DocumentHash.from_text("http://example.com", "Title", "Content")
        assert dh.url == "http://example.com"
        assert dh.content_hash != ""
        assert dh.title_hash != ""
        assert dh.fingerprint != ""


class TestDeduplicationEngine:
    """Tests for DeduplicationEngine class."""

    def setup_method(self):
        self.engine = DeduplicationEngine()

    def test_is_duplicate_first_document(self):
        is_dup, original = self.engine.is_duplicate(
            "http://example.com/page1", "Title", "Content"
        )
        assert is_dup is False
        assert original is None

    def test_is_duplicate_exact_match(self):
        self.engine.is_duplicate("http://example.com/page1", "Title", "Content")
        is_dup, original = self.engine.is_duplicate(
            "http://example.com/page2", "Title", "Content"
        )
        assert is_dup is True
        assert original == "http://example.com/page1"

    def test_is_duplicate_different_content(self):
        self.engine.is_duplicate("http://example.com/page1", "Title", "Content A")
        is_dup, _original = self.engine.is_duplicate(
            "http://example.com/page2", "Title", "Content B"
        )
        assert is_dup is False

    def test_is_duplicate_same_content_different_title(self):
        """Same content with different titles is still a duplicate."""
        self.engine.is_duplicate("http://example.com/page1", "Title A", "Content")
        is_dup, original = self.engine.is_duplicate(
            "http://example.com/page2", "Title B", "Content"
        )
        assert is_dup is True
        assert original == "http://example.com/page1"

    def test_document_count(self):
        self.engine.is_duplicate("http://a.com", "T", "C1")
        self.engine.is_duplicate("http://b.com", "T", "C2")
        assert self.engine.document_count == 2

    def test_duplicate_count(self):
        self.engine.is_duplicate("http://a.com", "T", "C1")
        self.engine.is_duplicate("http://b.com", "T", "C1")  # dup
        assert self.engine.duplicate_count == 1

    def test_clear(self):
        self.engine.is_duplicate("http://a.com", "T", "C1")
        self.engine.clear()
        assert self.engine.document_count == 0
        assert self.engine.duplicate_count == 0

    def test_get_original_url_for_duplicate(self):
        self.engine.is_duplicate("http://original.com", "T", "Content")
        self.engine.is_duplicate("http://copy.com", "T", "Content")
        original = self.engine.get_original_url("http://copy.com")
        assert original == "http://original.com"

    def test_get_original_url_for_unique(self):
        self.engine.is_duplicate("http://unique.com", "T", "Content")
        original = self.engine.get_original_url("http://unique.com")
        assert original is None

    def test_get_original_url_unknown(self):
        original = self.engine.get_original_url("http://unknown.com")
        assert original is None

    def test_is_near_duplicate_no_duplicates(self):
        self.engine.is_duplicate("http://a.com", "T", "Content A")
        is_dup, _url, _score = self.engine.is_near_duplicate(
            "http://b.com", "T", "Content B"
        )
        assert is_dup is False

    def test_is_near_duplicate_empty_content(self):
        is_dup, _url, score = self.engine.is_near_duplicate(
            "http://a.com", "T", ""
        )
        assert is_dup is False
        assert score == 0.0

    def test_custom_similarity_threshold(self):
        engine = DeduplicationEngine(similarity_threshold=0.5)
        assert engine._similarity_threshold == 0.5

    def test_multiple_duplicates_same_content(self):
        self.engine.is_duplicate("http://a.com", "T", "Same Content")
        is_dup1, orig1 = self.engine.is_duplicate("http://b.com", "T", "Same Content")
        is_dup2, orig2 = self.engine.is_duplicate("http://c.com", "T", "Same Content")
        assert is_dup1 is True
        assert is_dup2 is True
        assert orig1 == "http://a.com"
        assert orig2 == "http://a.com"


class TestFindDuplicates:
    """Tests for find_duplicates convenience function."""

    def test_find_duplicates_basic(self):
        result = find_duplicates(["a", "a", "b"])
        assert result == ["a"]

    def test_find_duplicates_no_dups(self):
        result = find_duplicates(["a", "b", "c"])
        assert result == []

    def test_find_duplicates_multiple(self):
        result = find_duplicates(["a", "b", "a", "b", "c"])
        assert result == ["a", "b"]

    def test_find_duplicates_empty(self):
        result = find_duplicates([])
        assert result == []


class TestRemoveDuplicates:
    """Tests for remove_duplicates convenience function."""

    def test_remove_duplicates_basic(self):
        result = remove_duplicates(["a", "a", "b"])
        assert result == ["a", "b"]

    def test_remove_duplicates_no_dups(self):
        result = remove_duplicates(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_remove_duplicates_preserves_order(self):
        result = remove_duplicates(["c", "b", "a", "b", "c"])
        assert result == ["c", "b", "a"]

    def test_remove_duplicates_empty(self):
        result = remove_duplicates([])
        assert result == []


class TestContentDeduplicator:
    """Tests for ContentDeduplicator class."""

    def test_find_duplicates_hash(self):
        long_content = "Hello world test content here with enough words to pass the minimum length threshold check"
        items = [
            {"url": "http://a.com", "title": "A", "content": long_content},
            {"url": "http://b.com", "title": "B", "content": long_content},
            {"url": "http://c.com", "title": "C", "content": "Different content entirely that is also long enough to pass the minimum length threshold check"},
        ]
        dedup = ContentDeduplicator(DedupConfig(method="hash"))
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 1

    def test_find_duplicates_no_dups(self):
        items = [
            {"url": "http://a.com", "title": "A", "content": "Content A is unique here with enough words to pass the minimum length threshold check"},
            {"url": "http://b.com", "title": "B", "content": "Content B is unique here with enough words to pass the minimum length threshold check"},
        ]
        dedup = ContentDeduplicator(DedupConfig(method="hash"))
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0

    def test_add_items_detects_duplicate(self):
        long_content = "Hello world test content here with enough words to pass the minimum length threshold check"
        items = [
            {"url": "http://a.com", "title": "A", "content": long_content},
            {"url": "http://b.com", "title": "B", "content": long_content},
        ]
        dedup = ContentDeduplicator(DedupConfig(method="hash"))
        result = dedup.add_items(items)
        assert isinstance(result, AddItemResult)

    def test_dedup_result_ratio(self):
        result = DedupResult(total_items=10, unique_items=7, duplicate_groups=1)
        assert result.duplicate_ratio == 0.3

    def test_dedup_result_zero_total(self):
        result = DedupResult(total_items=0, unique_items=0)
        assert result.duplicate_ratio == 0.0

    def test_duplicate_group_total_count(self):
        group = DuplicateGroup(representative="http://a.com", duplicates=["http://b.com"])
        assert group.total_count == 2

    def test_batch_report_to_dict(self):
        result = DedupResult(
            total_items=10,
            unique_items=8,
            duplicate_groups=1,
            groups=[DuplicateGroup(representative="http://a.com", duplicates=["http://b.com"], similarity_score=1.0)],
        )
        report = BatchDedupReport(result)
        d = report.to_dict()
        assert d["total_items"] == 10
        assert d["duplicate_groups"] == 1

    def test_batch_report_summary_string(self):
        result = DedupResult(
            total_items=10,
            unique_items=8,
            duplicate_groups=1,
            groups=[DuplicateGroup(representative="http://a.com", duplicates=["http://b.com"], similarity_score=1.0)],
        )
        report = BatchDedupReport(result)
        summary = report.to_summary_string()
        assert "Total items: 10" in summary
        assert "http://a.com" in summary

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError):
            DedupConfig(method="invalid")


class TestSimilarityMethod:
    """Tests for SimilarityMethod enum."""

    def test_hash_method(self):
        assert SimilarityMethod.HASH.value == "hash"

    def test_tfidf_method(self):
        assert SimilarityMethod.TFIDF.value == "tfidf"

    def test_jaccard_method(self):
        assert SimilarityMethod.JACCARD.value == "jaccard"
