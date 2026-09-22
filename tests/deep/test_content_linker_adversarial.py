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


class TestSimilarityEngineNoneAndCache:
    """Adversarial pins for None inputs and the cache-write contract.

    The existing deep test covered empty-string and whitespace inputs but never
    None (a falsy non-string) nor the documented "no cache entry is written"
    guarantee for the empty / no-token guards.
    """

    def test_tokenize_none_returns_empty(self):
        # None is falsy -> the `if not text` guard returns [] (no AttributeError).
        assert _tokenize(None) == []

    def test_similarity_none_scores_zero(self):
        # A None argument is falsy -> the `if not text_a or not text_b` guard
        # returns 0.0 without touching the cache.
        s = SimilarityEngine()
        assert s.similarity(None, "hello") == 0.0
        assert s.similarity("hello", None) == 0.0
        assert s.similarity(None, None) == 0.0

    def test_empty_input_writes_no_cache_entry(self):
        # Contract: "if text_a or text_b is falsy ... no cache entry is written."
        s = SimilarityEngine()
        s.similarity("", "hello")
        s.similarity("hello", "")
        s.similarity("", "")
        assert s._cache == {}

    def test_no_token_guard_writes_no_cache_entry(self):
        # Contract: the no-token guard returns 0.0 before the cache write, so a
        # punctuation-only pair must not poison the cache.
        s = SimilarityEngine()
        s.similarity("!!!", "hello world")
        assert s._cache == {}

    def test_none_writes_no_cache_entry(self):
        s = SimilarityEngine()
        s.similarity(None, "hello")
        assert s._cache == {}


class TestSimilarityEngineBoundary:
    """Adversarial pins for find_similar threshold / ordering boundaries."""

    def test_find_similar_threshold_zero_keeps_zero_score(self):
        # threshold=0 is inclusive (>=), so a zero-score item is kept, not
        # dropped. The 1.0 item sorts first, the 0.0 item last.
        s = SimilarityEngine()
        res = s.find_similar("hello", [("z", "nope"), ("a", "hello")], threshold=0)
        assert [(r["id"], r["score"]) for r in res] == [("a", 1.0), ("z", 0.0)]

    def test_find_similar_sort_is_stable_on_ties(self):
        # Equal scores keep insertion order (Python sort is stable), so the
        # result order is deterministic, not arbitrary.
        s = SimilarityEngine()
        res = s.find_similar("hello", [("z", "hello"), ("a", "hello"), ("m", "hello")], threshold=0.1)
        assert [r["id"] for r in res] == ["z", "a", "m"]

    def test_jaccard_exact_value(self):
        # tokens_a={a,b,c}, tokens_b={a,b}: intersection=2, union=3 -> 2/3.
        s = SimilarityEngine()
        assert abs(s.similarity("a b c", "a b") - 2 / 3) < 1e-9

    def test_find_similar_limit_one(self):
        # limit=1 keeps exactly the top-scoring item.
        s = SimilarityEngine()
        res = s.find_similar("hello", [("a", "hello"), ("b", "hello world")], limit=1)
        assert len(res) == 1
        assert res[0]["id"] == "a"

    def test_find_similar_single_element_collection(self):
        # A one-element collection is a valid input, not an error.
        s = SimilarityEngine()
        res = s.find_similar("hello", [("only", "hello")])
        assert res == [{"id": "only", "score": 1.0}]


class TestContentLinkerBoundary:
    """Adversarial pins for ContentLinker store / scoring boundaries."""

    def test_saved_at_auto_stamped_as_iso_string(self):
        # add_item with no saved_at stamps a UTC ISO-8601 string (not None).
        linker = ContentLinker()
        linker.add_item("1", "x")
        item = linker.get_item("1")
        assert isinstance(item["saved_at"], str)
        assert item["saved_at"] != ""

    def test_add_item_overwrites_same_id(self):
        # Re-adding the same id replaces the record; the store holds one item.
        linker = ContentLinker()
        linker.add_item("1", "old content")
        linker.add_item("1", "new content")
        assert len(linker.get_all_items()) == 1
        assert linker.get_item("1")["content"] == "new content"

    def test_domain_is_lowercased(self):
        # urlparse().hostname lowercases the host; an uppercase URL still yields
        # the lowercase domain.
        linker = ContentLinker()
        linker.add_item("1", "x", url="HTTP://EXAMPLE.COM/PATH?Q=1")
        assert linker.get_item("1")["domain"] == "example.com"

    def test_domain_with_path_and_query(self):
        # Only the host is kept; path and query are stripped.
        linker = ContentLinker()
        linker.add_item("1", "x", url="https://sub.example.org/a/b?c=d")
        assert linker.get_item("1")["domain"] == "sub.example.org"

    def test_temporal_boundary_exactly_24h_no_boost(self):
        # h == 24 is NOT < 24, so exactly-24h-apart items get no temporal boost.
        linker = ContentLinker()
        linker.add_item("1", "hello", saved_at="2026-01-01T00:00:00+00:00")
        linker.add_item("2", "hello", saved_at="2026-01-02T00:00:00+00:00")
        results = linker.find_related("1")
        assert results, "content match expected"
        assert not any("temporal" in r["reasons"] for r in results)

    def test_temporal_just_under_24h_gets_boost(self):
        # 23h apart is < 24, so the temporal boost fires.
        linker = ContentLinker()
        linker.add_item("1", "hello", saved_at="2026-01-01T00:00:00+00:00")
        linker.add_item("2", "hello", saved_at="2026-01-01T23:00:00+00:00")
        results = linker.find_related("1")
        assert any("temporal" in r["reasons"] for r in results)

    def test_domain_bonus_reason(self):
        # Same domain + different content -> a domain reason and a 0.3+ score,
        # even with no content overlap.
        linker = ContentLinker()
        linker.add_item("1", "aaa", url="http://example.com")
        linker.add_item("2", "zzz", url="http://example.com")
        results = linker.find_related("1", threshold=0.1)
        assert results, "domain match expected"
        assert any("domain" in r["reasons"] for r in results)
        assert all(r["score"] >= 0.3 for r in results)

    def test_score_is_rounded_to_three_places(self):
        # find_related rounds each score to 3 decimals (1/3 content -> 0.333).
        linker = ContentLinker()
        linker.add_item("1", "a b c", saved_at="2020-01-01T00:00:00+00:00")
        linker.add_item("2", "a b", saved_at="2026-01-01T00:00:00+00:00")
        results = linker.find_related("1")
        assert results
        assert results[0]["score"] == round(results[0]["score"], 3)

    def test_find_related_excludes_self(self):
        # The source item is never reported as related to itself, even when it
        # is the only item (identical content would otherwise score 1.0).
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        assert linker.find_related("1") == []

    def test_get_all_links_link_type_is_content(self):
        # get_all_links wraps every related item as a CONTENT-type Link.
        from personal_index.content_linker.link import LinkType

        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "hello world")
        links = linker.get_all_links("1")
        assert links
        assert all(lk.link_type is LinkType.CONTENT for lk in links)
        assert all(lk.source_id == "1" for lk in links)

    def test_get_all_items_empty_store(self):
        # A fresh linker has no items.
        linker = ContentLinker()
        assert linker.get_all_items() == []

    def test_remove_item_invalidates_its_cache(self):
        # Removing an item also drops its cached related-results.
        linker = ContentLinker()
        linker.add_item("1", "hello world")
        linker.add_item("2", "world peace")
        linker.find_related("1")
        assert "1" in linker._link_cache
        linker.remove_item("1")
        assert "1" not in linker._link_cache
        assert linker.get_item("1") is None


class TestLinkBoundary:
    """Adversarial pins for the Link data model boundaries."""

    def test_from_dict_missing_source_id_raises_keyerror(self):
        # source_id/target_id are required (data["source_id"]), so a missing
        # key raises KeyError, not a silent default.
        from personal_index.content_linker.link import Link

        try:
            Link.from_dict({"target_id": "y"})
            raised = False
        except KeyError:
            raised = True
        assert raised

    def test_from_dict_missing_target_id_raises_keyerror(self):
        from personal_index.content_linker.link import Link

        try:
            Link.from_dict({"source_id": "x"})
            raised = False
        except KeyError:
            raised = True
        assert raised

    def test_all_link_types_round_trip(self):
        # Every LinkType member survives a to_dict -> from_dict round-trip.
        from personal_index.content_linker.link import Link, LinkType

        for lt in LinkType:
            link = Link("a", "b", lt, 0.42)
            assert Link.from_dict(link.to_dict()) == link
            assert Link.from_dict(link.to_dict()).link_type is lt

    def test_link_type_has_exactly_five_members(self):
        # Pin the enum's member set so an accidental add/remove is caught.
        from personal_index.content_linker.link import LinkType

        assert {t.value for t in LinkType} == {"topic", "keyword", "domain", "temporal", "content"}

    def test_to_dict_has_exactly_four_keys(self):
        from personal_index.content_linker.link import Link

        d = Link("a", "b").to_dict()
        assert set(d.keys()) == {"source_id", "target_id", "link_type", "score"}
