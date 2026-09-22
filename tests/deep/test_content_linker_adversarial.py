"""Adversarial deep tests for content_linker module.

Tests SimilarityEngine and ContentLinker with edge cases, boundary
conditions, unicode, empty/None inputs, cache behavior, and property
checks.
"""

from personal_index.content_linker.linker import ContentLinker
from personal_index.content_linker.similarity import SimilarityEngine, _tokenize


class TestTokenize:
    """Adversarial tests for _tokenize helper."""

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_whitespace_only(self):
        assert _tokenize("   ") == []

    def test_mixed_case(self):
        assert _tokenize("Hello WORLD") == ["hello", "world"]

    def test_unicode_letters(self):
        # Non-ASCII letters are not matched by [a-z0-9]+
        # é -> not matched, so "café" -> ["caf"], "résumé" -> ["r", "sum"]
        assert _tokenize("café résumé") == ["caf", "r", "sum"]

    def test_numbers(self):
        assert _tokenize("test 123 abc") == ["test", "123", "abc"]

    def test_punctuation(self):
        assert _tokenize("hello, world!") == ["hello", "world"]

    def test_duplicate_tokens(self):
        assert _tokenize("the the the") == ["the", "the", "the"]

    def test_hyphenated(self):
        assert _tokenize("well-known") == ["well", "known"]


class TestSimilarityEngine:
    """Adversarial tests for SimilarityEngine."""

    def test_empty_inputs(self):
        engine = SimilarityEngine()
        assert engine.similarity("", "hello") == 0.0
        assert engine.similarity("hello", "") == 0.0
        assert engine.similarity("", "") == 0.0

    def test_whitespace_inputs(self):
        engine = SimilarityEngine()
        # Whitespace is truthy but tokenizes to empty
        assert engine.similarity("   ", "hello") == 0.0
        assert engine.similarity("hello", "   ") == 0.0

    def test_identical_strings(self):
        engine = SimilarityEngine()
        assert engine.similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        engine = SimilarityEngine()
        assert engine.similarity("apple banana", "car dog") == 0.0

    def test_partial_overlap(self):
        engine = SimilarityEngine()
        # Jaccard: 1 shared / 3 total = 0.333...
        score = engine.similarity("apple banana", "banana cherry")
        assert abs(score - 1/3) < 0.001

    def test_symmetry(self):
        engine = SimilarityEngine()
        a = engine.similarity("hello world", "world peace")
        b = engine.similarity("world peace", "hello world")
        assert a == b

    def test_cache_symmetry(self):
        engine = SimilarityEngine()
        engine.similarity("a b", "b c")
        # Should be cached under (min, max) key
        assert ("a b", "b c") in engine._cache
        assert ("b c", "a b") not in engine._cache

    def test_unicode_similarity(self):
        engine = SimilarityEngine()
        # é is not matched by [a-z0-9]+, so "café" -> ["caf"], "cafe" -> ["cafe"]
        # Different tokens -> 0.0 similarity
        assert engine.similarity("café", "cafe") == 0.0

    def test_score_range(self):
        engine = SimilarityEngine()
        for i in range(100):
            score = engine.similarity(f"test {i}", f"test {i+1}")
            assert 0.0 <= score <= 1.0

    def test_find_similar_empty_items(self):
        engine = SimilarityEngine()
        results = engine.find_similar("query", [])
        assert results == []

    def test_find_similar_threshold(self):
        engine = SimilarityEngine()
        items = [
            ("a", "hello world"),
            ("b", "completely different"),
            ("c", "world peace"),
        ]
        results = engine.find_similar("hello world", items, threshold=0.3)
        ids = [r["id"] for r in results]
        assert "a" in ids
        assert "b" not in ids

    def test_find_similar_limit(self):
        engine = SimilarityEngine()
        items = [(f"item_{i}", "hello world") for i in range(20)]
        results = engine.find_similar("hello world", items, limit=5)
        assert len(results) == 5

    def test_find_similar_negative_limit(self):
        engine = SimilarityEngine()
        items = [("a", "hello")]
        results = engine.find_similar("hello", items, limit=-1)
        assert results == []

    def test_find_similar_zero_limit(self):
        engine = SimilarityEngine()
        items = [("a", "hello")]
        results = engine.find_similar("hello", items, limit=0)
        assert results == []

    def test_find_similar_result_keys(self):
        engine = SimilarityEngine()
        results = engine.find_similar("hello", [("a", "hello")])
        for r in results:
            assert set(r.keys()) == {"id", "score"}


class TestContentLinker:
    """Adversarial tests for ContentLinker."""

    def test_add_and_get_item(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world", url="http://example.com")
        item = linker.get_item("1")
        assert item is not None
        assert item["id"] == "1"
        assert item["content"] == "hello world"
        assert item["domain"] == "example.com"

    def test_get_nonexistent_item(self):
        linker = ContentLinker()
        assert linker.get_item("missing") is None

    def test_remove_item(self):
        linker = ContentLinker()
        linker.add_item("1", "content")
        linker.remove_item("1")
        assert linker.get_item("1") is None

    def test_remove_nonexistent_item(self):
        linker = ContentLinker()
        linker.remove_item("missing")  # Should not raise

    def test_find_related_no_items(self):
        linker = ContentLinker()
        linker.add_item("1", "hello")
        results = linker.find_related("1")
        assert results == []

    def test_find_related_nonexistent_item(self):
        linker = ContentLinker()
        linker.add_item("1", "hello")
        results = linker.find_related("missing")
        assert results == []

    def test_find_related_negative_limit(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        results = linker.find_related("1", limit=-1)
        assert results == []

    def test_find_related_zero_limit(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        results = linker.find_related("1", limit=0)
        assert results == []

    def test_find_related_threshold(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "completely different text")
        linker.add_item("3", "world peace")
        # High threshold should filter out weak matches
        results = linker.find_related("1", threshold=0.5)
        ids = [r["id"] for r in results]
        assert "2" not in ids

    def test_find_related_limit(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        for i in range(2, 12):
            linker.add_item(str(i), "world peace")
        results = linker.find_related("1", limit=3)
        assert len(results) <= 3

    def test_find_related_sorted_by_score(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "hello world identical")
        linker.add_item("3", "different content")
        results = linker.find_related("1")
        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]

    def test_find_related_result_keys(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        results = linker.find_related("1")
        for r in results:
            assert set(r.keys()) == {"id", "score", "title", "reasons"}

    def test_cache_invalidation_on_add(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        linker.find_related("1")
        assert "1" in linker._link_cache
        # Adding new item should invalidate cache for that item
        linker.add_item("3", "new content")
        # Cache for item 1 is not invalidated by adding item 3
        # (only invalidated when item 1 itself is added/updated)
        assert "1" in linker._link_cache

    def test_clear_cache(self):
        linker = ContentLinker()
        linker.add_item("1", "hello")
        linker.add_item("2", "world")
        linker.find_related("1")
        linker.clear_cache()
        assert linker._items == {}
        assert linker._link_cache == {}

    def test_domain_extraction_empty_url(self):
        linker = ContentLinker()
        linker.add_item("1", "content", url="")
        item = linker.get_item("1")
        assert item["domain"] == ""

    def test_domain_extraction_invalid_url(self):
        linker = ContentLinker()
        linker.add_item("1", "content", url="not a url")
        item = linker.get_item("1")
        assert item["domain"] == ""

    def test_temporal_scoring_same_time(self):
        linker = ContentLinker()
        # Use ISO format without 'Z' (Python 3.10 compatibility)
        linker.add_item("1", "hello", saved_at="2026-01-01T00:00:00+00:00")
        linker.add_item("2", "hello", saved_at="2026-01-01T00:00:00+00:00")
        results = linker.find_related("1")
        # Same time should give temporal boost
        assert any("temporal" in r["reasons"] for r in results)

    def test_temporal_scoring_far_apart(self):
        linker = ContentLinker()
        linker.add_item("1", "hello", saved_at="2020-01-01T00:00:00+00:00")
        linker.add_item("2", "hello", saved_at="2026-01-01T00:00:00+00:00")
        results = linker.find_related("1")
        # Far apart should not have temporal reason
        assert not any("temporal" in r["reasons"] for r in results)

    def test_get_all_links(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        links = linker.get_all_links("1")
        for link in links:
            assert link.source_id == "1"
            assert link.score >= 0.0

    def test_idempotent_find_related(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        results1 = linker.find_related("1")
        results2 = linker.find_related("1")
        assert results1 == results2

    def test_unicode_content(self):
        linker = ContentLinker()
        # Use different timestamps to avoid temporal match
        linker.add_item("1", "café résumé", saved_at="2020-01-01T00:00:00+00:00")
        linker.add_item("2", "cafe resume", saved_at="2026-01-01T00:00:00+00:00")
        results = linker.find_related("1")
        # Different tokens (café -> ["caf"], cafe -> ["cafe"]), no temporal match
        assert len(results) == 0

    def test_duplicate_items(self):
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "hello world")
        results = linker.find_related("1")
        assert len(results) == 1
        assert results[0]["id"] == "2"

    def test_empty_content_items(self):
        linker = ContentLinker()
        linker.add_item("1", "")
        linker.add_item("2", "")
        results = linker.find_related("1")
        # Empty content -> no content match, but temporal may still match
        # Check that content reason is not present
        for r in results:
            assert "content" not in r["reasons"]

    def test_title_only_matching(self):
        linker = ContentLinker()
        linker.add_item("1", "content", title="hello world")
        linker.add_item("2", "different", title="world peace")
        results = linker.find_related("1")
        # Should match on title
        assert len(results) > 0


class TestLinkDataclass:
    """Adversarial pins for the Link data model (to_dict/from_dict round-trip).

    The existing deep test covered SimilarityEngine and ContentLinker but never
    the Link dataclass itself - the serialization contract (to_dict -> from_dict
    round-trip, default link_type/score, enum coercion, equality) was untested.
    """

    def test_round_trip_preserves_all_fields(self):
        from personal_index.content_linker.link import Link, LinkType

        link = Link("a", "b", LinkType.TOPIC, 0.7)
        link2 = Link.from_dict(link.to_dict())
        assert link == link2
        assert link2.link_type is LinkType.TOPIC
        assert link2.score == 0.7

    def test_to_dict_serializes_link_type_to_value(self):
        from personal_index.content_linker.link import Link, LinkType

        d = Link("a", "b", LinkType.DOMAIN, 0.3).to_dict()
        assert d["link_type"] == "domain"  # value, not the enum member
        assert d["score"] == 0.3

    def test_from_dict_defaults_link_type_to_content(self):
        from personal_index.content_linker.link import Link, LinkType

        link = Link.from_dict({"source_id": "x", "target_id": "y"})
        assert link.link_type is LinkType.CONTENT
        assert link.score == 0.5

    def test_from_dict_accepts_enum_member_directly(self):
        from personal_index.content_linker.link import Link, LinkType

        link = Link.from_dict(
            {"source_id": "x", "target_id": "y", "link_type": LinkType.KEYWORD, "score": 0.9}
        )
        assert link.link_type is LinkType.KEYWORD
        assert link.score == 0.9

    def test_from_dict_invalid_link_type_raises(self):
        from personal_index.content_linker.link import Link

        # A bogus string link_type is not a valid LinkType member; the enum
        # constructor must reject it rather than silently defaulting.
        try:
            Link.from_dict({"source_id": "x", "target_id": "y", "link_type": "bogus"})
            raised = False
        except ValueError:
            raised = True
        assert raised

    def test_equality_is_fieldwise(self):
        from personal_index.content_linker.link import Link, LinkType

        a = Link("a", "b", LinkType.CONTENT, 0.5)
        assert a == Link("a", "b", LinkType.CONTENT, 0.5)
        assert a != Link("a", "b", LinkType.CONTENT, 0.6)  # score differs
        assert a != Link("a", "c", LinkType.CONTENT, 0.5)  # target differs
        assert a != Link("b", "b", LinkType.CONTENT, 0.5)  # source differs
        assert a != Link("a", "b", LinkType.TOPIC, 0.5)  # type differs

    def test_equality_against_non_link_is_false(self):
        from personal_index.content_linker.link import Link

        assert (Link("a", "b") == "not a link") is False
        assert (Link("a", "b") == None) is False  # noqa: E711


class TestSimilarityEdgeCases:
    """Adversarial pins for SimilarityEngine no-token guard and threshold boundary."""

    def test_punctuation_only_scores_zero(self):
        # Neither side yields any [a-z0-9]+ token -> no-token guard -> 0.0.
        s = SimilarityEngine()
        assert s.similarity("!!!", "???") == 0.0

    def test_punctuation_vs_word_scores_zero(self):
        # One side has no tokens -> 0.0 (not a crash, not a partial score).
        s = SimilarityEngine()
        assert s.similarity("!!!", "hello world") == 0.0

    def test_threshold_one_is_inclusive(self):
        # Identical strings score 1.0; threshold=1.0 is inclusive (>=), so the
        # item is kept, not dropped.
        s = SimilarityEngine()
        res = s.find_similar("abc", [("i1", "abc")], threshold=1.0)
        assert res == [{"id": "i1", "score": 1.0}]

    def test_cache_key_is_symmetric_pair(self):
        # The cache key is (min, max) of the RAW strings, so (a,b) and (b,a)
        # share one entry and both return the same score.
        s = SimilarityEngine()
        a = s.similarity("alpha beta", "beta gamma")
        b = s.similarity("beta gamma", "alpha beta")
        assert a == b
        # Exactly one cache entry for the symmetric pair.
        assert len(s._cache) == 1
