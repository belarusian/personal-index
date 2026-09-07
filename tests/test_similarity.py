"""Tests for similarity engine."""

from personal_index.content_linker.similarity import (
    SimilarityEngine,
    _tokenize,
)


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_empty(self):
        assert _tokenize("") == []



    def test_special_chars(self):
        tokens = _tokenize("Hello, World!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "," not in tokens

    def test_numbers(self):
        assert _tokenize("item 123") == ["item", "123"]


class TestSimilarityEngine:
    def test_identical(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello", "world") == 0.0

    def test_partial_overlap(self):
        eng = SimilarityEngine()
        score = eng.similarity("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    def test_empty_a(self):
        eng = SimilarityEngine()
        assert eng.similarity("", "hello") == 0.0

    def test_empty_b(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello", "") == 0.0

    def test_cache_used(self):
        eng = SimilarityEngine()
        s1 = eng.similarity("aaa bbb", "aaa ccc")
        s2 = eng.similarity("aaa bbb", "aaa ccc")
        assert s1 == s2
        assert len(eng._cache) == 1

    def test_cache_key_order_independent(self):
        eng = SimilarityEngine()
        eng.similarity("zzz", "aaa")
        assert ("aaa", "zzz") in eng._cache

    def test_find_similar(self):
        eng = SimilarityEngine()
        items = [
            ("id1", "hello world"),
            ("id2", "goodbye world"),
            ("id3", "completely different"),
        ]
        results = eng.find_similar("hello world", items, threshold=0.3)
        assert len(results) >= 1
        assert results[0]["id"] == "id1"

    def test_find_similar_threshold(self):
        eng = SimilarityEngine()
        items = [("id1", "hello world"), ("id2", "aaa bbb")]
        results = eng.find_similar("hello world", items, threshold=0.9)
        assert len(results) == 1
        assert results[0]["id"] == "id1"

    def test_find_similar_limit(self):
        eng = SimilarityEngine()
        items = [(f"id{i}", "hello world") for i in range(10)]
        results = eng.find_similar("hello world", items, limit=3)
        assert len(results) == 3

    def test_find_similar_sorted(self):
        eng = SimilarityEngine()
        items = [("id1", "hello world foo"), ("id2", "hello world")]
        results = eng.find_similar("hello world", items)
        assert results[0]["score"] >= results[1]["score"]

    def test_find_similar_empty_items(self):
        eng = SimilarityEngine()
        results = eng.find_similar("hello", [])
        assert results == []

    def test_jaccard_calculation(self):
        eng = SimilarityEngine()
        score = eng.similarity("a b c", "c d e")
        assert score == 1 / 5


class TestSimilarityEngineDocstring553:
    """Pinning test for the exact-contract docstrings (TICKET-553)."""

    def test_similarity_docstring_states_exact_contract(self) -> None:
        doc = (SimilarityEngine.similarity.__doc__ or "").lower()
        for fragment in (
            "jaccard index",
            "symmetric pair",
            "no-token guard",
            "no cache entry is written",
        ):
            assert fragment in doc, f"missing fragment: {fragment!r}"

    def test_find_similar_docstring_states_exact_contract(self) -> None:
        doc = (SimilarityEngine.find_similar.__doc__ or "").lower()
        for fragment in (
            "descending",
            "truncated to the first",
            "inclusive",
            "exactly the keys",
        ):
            assert fragment in doc, f"missing fragment: {fragment!r}"

    def test_empty_string_scores_zero(self) -> None:
        eng = SimilarityEngine()
        assert eng.similarity("", "hello") == 0.0
        assert eng.similarity("hello", "") == 0.0

    def test_whitespace_only_scores_zero(self) -> None:
        eng = SimilarityEngine()
        # whitespace-only is truthy -> falls through to the no-token guard
        assert eng.similarity("   ", "hello") == 0.0
        assert eng.similarity("hello", "\t\n") == 0.0

    def test_cache_key_is_symmetric_raw_pair(self) -> None:
        eng = SimilarityEngine()
        a, b = "zzz aaa", "mmm nnn"
        eng.similarity(a, b)
        assert len(eng._cache) == 1
        assert (min(a, b), max(a, b)) in eng._cache

    def test_jaccard_score(self) -> None:
        eng = SimilarityEngine()
        # {a,b,c} & {c,d,e} = {c}; union = {a,b,c,d,e} -> 1/5
        assert eng.similarity("a b c", "c d e") == 1 / 5

    def test_find_similar_threshold_inclusive(self) -> None:
        eng = SimilarityEngine()
        # identical content scores 1.0, so threshold=1.0 keeps it
        results = eng.find_similar("hello world", [("x", "hello world")], threshold=1.0)
        assert results == [{"id": "x", "score": 1.0}]

    def test_find_similar_sorted_descending(self) -> None:
        eng = SimilarityEngine()
        items = [
            ("low", "completely different words here"),
            ("high", "hello world"),
            ("mid", "hello world foo"),
        ]
        results = eng.find_similar("hello world", items, threshold=0.0)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_find_similar_limit_truncates(self) -> None:
        eng = SimilarityEngine()
        items = [(f"i{n}", "hello world") for n in range(5)]
        results = eng.find_similar("hello world", items, threshold=0.0, limit=3)
        assert len(results) == 3

    def test_find_similar_result_dict_shape(self) -> None:
        eng = SimilarityEngine()
        results = eng.find_similar("hello world", [("x", "hello world")], threshold=0.0)
        assert results
        for r in results:
            assert set(r.keys()) == {"id", "score"}
