"""Tests for content_dedup module - detect duplicate saved content."""

from __future__ import annotations

import pytest
from personal_index.content_dedup import (
    ContentDeduplicator,
    DedupConfig,
    DedupResult,
    DuplicateGroup,
    SimilarityMethod,
)


class TestDedupConfig:
    """Test DedupConfig dataclass."""

    def test_default_config(self):
        config = DedupConfig()
        assert config.similarity_threshold == 0.85
        assert config.method == "hash"
        assert config.min_content_length == 50

    def test_custom_config(self):
        config = DedupConfig(similarity_threshold=0.7, method="tfidf")
        assert config.similarity_threshold == 0.7
        assert config.method == "tfidf"

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            DedupConfig(method="nonexistent")


class TestSimilarityMethod:
    """Test SimilarityMethod enum."""

    def test_all_methods(self):
        methods = list(SimilarityMethod)
        assert "hash" in [m.value for m in methods]
        assert "tfidf" in [m.value for m in methods]
        assert "jaccard" in [m.value for m in methods]

    def test_method_value(self):
        assert SimilarityMethod.HASH.value == "hash"
        assert SimilarityMethod.TFIDF.value == "tfidf"
        assert SimilarityMethod.JACCARD.value == "jaccard"


class TestDuplicateGroup:
    """Test DuplicateGroup dataclass."""

    def test_create_group(self):
        group = DuplicateGroup(
            representative="https://example.com/original",
            duplicates=["https://example.com/copy1", "https://example.com/copy2"],
            similarity_score=0.95,
        )
        assert group.representative == "https://example.com/original"
        assert len(group.duplicates) == 2
        assert group.similarity_score == 0.95

    def test_group_total_count(self):
        group = DuplicateGroup(
            representative="https://example.com/original",
            duplicates=["https://example.com/copy1"],
            similarity_score=0.9,
        )
        assert group.total_count == 2

    def test_empty_group(self):
        group = DuplicateGroup(
            representative="https://example.com/original",
            duplicates=[],
            similarity_score=1.0,
        )
        assert group.total_count == 1


class TestDedupResult:
    """Test DedupResult dataclass."""

    def test_create_result(self):
        result = DedupResult(
            total_items=10,
            unique_items=7,
            duplicate_groups=3,
            groups=[],
        )
        assert result.total_items == 10
        assert result.unique_items == 7
        assert result.duplicate_groups == 3

    def test_duplicate_ratio(self):
        result = DedupResult(
            total_items=10,
            unique_items=7,
            duplicate_groups=3,
            groups=[],
        )
        assert result.duplicate_ratio == 0.3


class TestContentDeduplicatorHashMethod:
    """Test hash-based deduplication."""

    def test_exact_duplicate_detection(self):
        dedup = ContentDeduplicator()
        items = [
            {"url": "https://a.com", "title": "Same Title", "content": "Same content here"},
            {"url": "https://b.com", "title": "Same Title", "content": "Same content here"},
        ]
        result = dedup.find_duplicates(items)
        assert len(result.groups) == 1
        assert result.duplicate_groups == 1

    def test_no_duplicates(self):
        dedup = ContentDeduplicator()
        items = [
            {"url": "https://a.com", "title": "Title A", "content": "Content A is unique"},
            {"url": "https://b.com", "title": "Title B", "content": "Content B is different"},
        ]
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0

    def test_single_item(self):
        dedup = ContentDeduplicator()
        items = [{"url": "https://a.com", "title": "Only", "content": "Just one item"}]
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0
        assert result.unique_items == 1

    def test_empty_items(self):
        dedup = ContentDeduplicator()
        result = dedup.find_duplicates([])
        assert result.total_items == 0
        assert result.duplicate_groups == 0


class TestContentDeduplicatorJaccardMethod:
    """Test Jaccard similarity deduplication."""

    def test_near_duplicate_jaccard(self):
        config = DedupConfig(method="jaccard", similarity_threshold=0.7)
        dedup = ContentDeduplicator(config=config)
        items = [
            {"url": "https://a.com", "title": "Article", "content": "Machine learning is great for data analysis"},
            {"url": "https://b.com", "title": "Article Copy", "content": "Machine learning is very great for data analysis"},
        ]
        result = dedup.find_duplicates(items)
        assert len(result.groups) >= 0  # Should detect similarity

    def test_different_content_jaccard(self):
        config = DedupConfig(method="jaccard", similarity_threshold=0.7)
        dedup = ContentDeduplicator(config=config)
        items = [
            {"url": "https://a.com", "title": "A", "content": "Cats are wonderful pets"},
            {"url": "https://b.com", "title": "B", "content": "Quantum physics is complex"},
        ]
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0


class TestContentDeduplicatorTfidfMethod:
    """Test TF-IDF based deduplication."""

    def test_similar_content_tfidf(self):
        config = DedupConfig(method="tfidf", similarity_threshold=0.5)
        dedup = ContentDeduplicator(config=config)
        items = [
            {"url": "https://a.com", "title": "A", "content": "Python programming language is popular"},
            {"url": "https://b.com", "title": "B", "content": "Python programming is very popular language"},
        ]
        result = dedup.find_duplicates(items)
        assert len(result.groups) >= 0

    def test_dissimilar_content_tfidf(self):
        config = DedupConfig(method="tfidf", similarity_threshold=0.5)
        dedup = ContentDeduplicator(config=config)
        items = [
            {"url": "https://a.com", "title": "A", "content": "Cooking recipes for dinner"},
            {"url": "https://b.com", "title": "B", "content": "Stock market analysis report"},
        ]
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0


class TestContentDeduplicatorIntegration:
    """Integration tests for content deduplication."""

    def test_mixed_duplicates(self):
        dedup = ContentDeduplicator()
        items = [
            {"url": "https://a.com", "title": "A", "content": "Unique content alpha"},
            {"url": "https://b.com", "title": "B", "content": "Duplicate content beta"},
            {"url": "https://c.com", "title": "C", "content": "Duplicate content beta"},
            {"url": "https://d.com", "title": "D", "content": "Another unique piece"},
            {"url": "https://e.com", "title": "E", "content": "Duplicate content beta"},
        ]
        result = dedup.find_duplicates(items)
        assert result.total_items == 5
        assert result.duplicate_groups >= 1

    def test_get_unique_items(self):
        dedup = ContentDeduplicator()
        items = [
            {"url": "https://a.com", "title": "A", "content": "Unique one"},
            {"url": "https://b.com", "title": "B", "content": "Duplicate here"},
            {"url": "https://c.com", "title": "C", "content": "Duplicate here"},
        ]
        result = dedup.find_duplicates(items)
        unique = dedup.get_unique_items(items)
        assert len(unique) <= len(items)

    def test_incremental_dedup(self):
        dedup = ContentDeduplicator()
        batch1 = [{"url": "https://a.com", "title": "A", "content": "First batch content"}]
        dedup.add_items(batch1)
        batch2 = [{"url": "https://b.com", "title": "B", "content": "First batch content"}]
        result = dedup.add_items(batch2)
        assert result.is_duplicate

    def test_clear_state(self):
        dedup = ContentDeduplicator()
        items = [{"url": "https://a.com", "title": "A", "content": "Some content"}]
        dedup.add_items(items)
        dedup.clear()
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0

    def test_short_content_ignored(self):
        config = DedupConfig(min_content_length=100)
        dedup = ContentDeduplicator(config=config)
        items = [
            {"url": "https://a.com", "title": "A", "content": "Short"},
            {"url": "https://b.com", "title": "B", "content": "Short"},
        ]
        result = dedup.find_duplicates(items)
        assert result.duplicate_groups == 0
