"""Tests for content_linker module - find related saved items."""

import pytest
from datetime import datetime, timezone, timedelta

from personal_index.content_linker.link import Link, LinkType
from personal_index.content_linker.similarity import SimilarityEngine
from personal_index.content_linker.linker import ContentLinker


# ── Link model tests ───────────────────────────────────────

class TestLink:
    def test_create_link(self):
        link = Link(source_id="a1", target_id="b2", link_type=LinkType.TOPIC)
        assert link.source_id == "a1"
        assert link.target_id == "b2"
        assert link.link_type == LinkType.TOPIC

    def test_link_default_score(self):
        link = Link(source_id="a", target_id="b")
        assert link.score == 0.5

    def test_link_to_dict(self):
        link = Link(source_id="x", target_id="y", score=0.8)
        d = link.to_dict()
        assert d["source_id"] == "x"
        assert d["target_id"] == "y"
        assert d["score"] == 0.8

    def test_link_from_dict(self):
        d = {"source_id": "p", "target_id": "q", "score": 0.9, "link_type": "keyword"}
        link = Link.from_dict(d)
        assert link.source_id == "p"
        assert link.target_id == "q"
        assert link.score == 0.9

    def test_link_equality(self):
        l1 = Link("a", "b", LinkType.TOPIC, 0.7)
        l2 = Link("a", "b", LinkType.TOPIC, 0.7)
        assert l1 == l2

    def test_link_inequality(self):
        l1 = Link("a", "b", LinkType.TOPIC, 0.7)
        l2 = Link("a", "c", LinkType.TOPIC, 0.7)
        assert l1 != l2


class TestLinkType:
    def test_link_type_values(self):
        assert LinkType.TOPIC.value == "topic"
        assert LinkType.KEYWORD.value == "keyword"
        assert LinkType.DOMAIN.value == "domain"
        assert LinkType.TEMPORAL.value == "temporal"
        assert LinkType.CONTENT.value == "content"

    def test_link_type_count(self):
        assert len(LinkType) == 5


# ── SimilarityEngine tests ─────────────────────────────────

class TestSimilarityEngine:
    def test_similar_keywords(self):
        engine = SimilarityEngine()
        score = engine.similarity(
            "python programming tutorial",
            "python code examples"
        )
        assert score > 0

    def test_no_similarity(self):
        engine = SimilarityEngine()
        score = engine.similarity(
            "python programming",
            "cooking recipes baking"
        )
        assert score < 0.3

    def test_identical_text(self):
        engine = SimilarityEngine()
        score = engine.similarity("hello world", "hello world")
        assert score == 1.0

    def test_empty_text(self):
        engine = SimilarityEngine()
        score = engine.similarity("", "something")
        assert score == 0.0

    def test_both_empty(self):
        engine = SimilarityEngine()
        score = engine.similarity("", "")
        assert score == 0.0

    def test_similarity_symmetric(self):
        engine = SimilarityEngine()
        s1 = engine.similarity("abc def", "def ghi")
        s2 = engine.similarity("def ghi", "abc def")
        assert s1 == s2

    def test_similarity_range(self):
        engine = SimilarityEngine()
        score = engine.similarity("test", "test")
        assert 0.0 <= score <= 1.0

    def test_find_similar(self):
        engine = SimilarityEngine()
        items = [
            ("id1", "python web framework django"),
            ("id2", "javascript frontend react"),
            ("id3", "python data science pandas"),
        ]
        results = engine.find_similar("python programming", items, threshold=0.1)
        assert len(results) >= 1
        assert all(r["id"] in ("id1", "id3") for r in results)

    def test_find_similar_no_results(self):
        engine = SimilarityEngine()
        items = [("id1", "cooking baking")]
        results = engine.find_similar("quantum physics", items, threshold=0.9)
        assert len(results) == 0

    def test_find_similar_limit(self):
        engine = SimilarityEngine()
        items = [
            (f"id{i}", "python programming") for i in range(10)
        ]
        results = engine.find_similar("python code", items, limit=3)
        assert len(results) <= 3


# ── ContentLinker tests ────────────────────────────────────

class TestContentLinker:
    def test_add_item(self):
        linker = ContentLinker()
        linker.add_item("id1", "python programming tutorial")
        assert linker.get_item("id1") is not None

    def test_find_related(self):
        linker = ContentLinker()
        linker.add_item("id1", "python web development")
        linker.add_item("id2", "javascript frontend")
        linker.add_item("id3", "python data science")
        related = linker.find_related("id1", threshold=0.1)
        assert len(related) > 0

    def test_find_related_nonexistent(self):
        linker = ContentLinker()
        related = linker.find_related("nonexistent")
        assert len(related) == 0

    def test_remove_item(self):
        linker = ContentLinker()
        linker.add_item("id1", "some content")
        linker.remove_item("id1")
        assert linker.get_item("id1") is None

    def test_get_all_links(self):
        linker = ContentLinker()
        linker.add_item("id1", "python programming")
        linker.add_item("id2", "python code")
        links = linker.get_all_links("id1", threshold=0.1)
        assert isinstance(links, list)

    def test_link_by_domain(self):
        linker = ContentLinker()
        linker.add_item("id1", "python tutorial", url="https://example.com/page1")
        linker.add_item("id2", "another page", url="https://example.com/page2")
        related = linker.find_related("id1", threshold=0.0)
        assert any(r["id"] == "id2" for r in related)

    def test_link_by_temporal(self):
        linker = ContentLinker()
        now = datetime.now(timezone.utc)
        linker.add_item("id1", "recent post", saved_at=now.isoformat())
        linker.add_item("id2", "also recent", saved_at=(now - timedelta(hours=1)).isoformat())
        linker.add_item("id3", "old post", saved_at=(now - timedelta(days=365)).isoformat())
        related = linker.find_related("id1", threshold=0.0)
        assert any(r["id"] == "id2" for r in related)

    def test_clear_cache(self):
        linker = ContentLinker()
        linker.add_item("id1", "content")
        linker.clear_cache()
        assert len(linker.get_all_items()) == 0

    def test_get_item(self):
        linker = ContentLinker()
        linker.add_item("id1", "test content", url="https://test.com")
        item = linker.get_item("id1")
        assert item is not None
        assert item["content"] == "test content"

    def test_get_all_items(self):
        linker = ContentLinker()
        linker.add_item("id1", "content1")
        linker.add_item("id2", "content2")
        items = linker.get_all_items()
        assert len(items) == 2
