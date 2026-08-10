"""Tests for content deduplication module."""

from __future__ import annotations

import pytest

from personal_index.dedup import DeduplicationEngine, DocumentHash


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
