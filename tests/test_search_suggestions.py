"""Tests for personal_index.search_suggestions module."""

from __future__ import annotations

import time

import pytest

from personal_index.search_suggestions import (
    SearchSuggestions,
    Suggestion,
    TrendingEntry,
    _fuzzy_match_score,
)

# ── Suggestion tests ───────────────────────────────────────────────

class TestSuggestion:
    """Tests for the Suggestion dataclass."""

    def test_to_dict_serialization(self) -> None:
        s = Suggestion(text="python", score=0.85, source="history", category="tag")
        d = s.to_dict()
        assert d == {
            "text": "python",
            "score": 0.85,
            "source": "history",
            "category": "tag",
        }

    def test_to_dict_rounds_score(self) -> None:
        s = Suggestion(text="test", score=0.123456789)
        d = s.to_dict()
        assert d["score"] == 0.1235

    def test_to_dict_default_values(self) -> None:
        s = Suggestion(text="hello")
        d = s.to_dict()
        assert d["score"] == 0.0
        assert d["source"] == "unknown"
        assert d["category"] == ""


# ── TrendingEntry tests ────────────────────────────────────────────

class TestTrendingEntry:
    """Tests for the TrendingEntry dataclass."""

    def test_record_increments_count(self) -> None:
        entry = TrendingEntry(query="python")
        assert entry.count == 1
        entry.record()
        assert entry.count == 2
        entry.record()
        assert entry.count == 3

    def test_record_updates_last_seen(self) -> None:
        entry = TrendingEntry(query="python")
        old_last_seen = entry.last_seen
        time.sleep(0.01)
        entry.record()
        assert entry.last_seen > old_last_seen

    def test_age_seconds_positive(self) -> None:
        entry = TrendingEntry(query="python")
        time.sleep(0.01)
        assert entry.age_seconds > 0

    def test_age_seconds_near_zero_on_creation(self) -> None:
        entry = TrendingEntry(query="python")
        assert entry.age_seconds >= 0
        assert entry.age_seconds < 1.0

    def test_default_first_seen_and_last_seen(self) -> None:
        entry = TrendingEntry(query="test")
        assert entry.first_seen > 0
        assert entry.last_seen > 0


# ── _fuzzy_match_score tests ───────────────────────────────────────

class TestFuzzyMatchScore:
    """Tests for the _fuzzy_match_score function."""

    def test_exact_match_returns_one(self) -> None:
        assert _fuzzy_match_score("python", "python") == 1.0

    def test_exact_match_case_insensitive(self) -> None:
        assert _fuzzy_match_score("Python", "python") == 1.0

    def test_prefix_match_above_0_7(self) -> None:
        score = _fuzzy_match_score("pyt", "python")
        assert score > 0.7

    def test_prefix_match_short_prefix(self) -> None:
        score = _fuzzy_match_score("p", "python")
        assert score > 0.7

    def test_empty_query_returns_zero(self) -> None:
        assert _fuzzy_match_score("", "python") == 0.0

    def test_empty_candidate_returns_zero(self) -> None:
        assert _fuzzy_match_score("python", "") == 0.0

    def test_both_empty_returns_zero(self) -> None:
        assert _fuzzy_match_score("", "") == 0.0

    def test_partial_fuzzy_match(self) -> None:
        score = _fuzzy_match_score("pyton", "python")
        assert 0.0 < score < 1.0

    def test_completely_different(self) -> None:
        score = _fuzzy_match_score("abc", "xyz")
        assert score < 0.5

    def test_contains_match(self) -> None:
        score = _fuzzy_match_score("yth", "python")
        assert score == 0.8


# ── SearchSuggestions tests ────────────────────────────────────────

class TestSearchSuggestions:
    """Tests for the SearchSuggestions class."""

    @pytest.fixture
    def suggestions(self) -> SearchSuggestions:
        s = SearchSuggestions(max_suggestions=10, min_prefix_length=2)
        s.add_search_history([
            "python tutorial",
            "python web",
            "python data",
            "javascript basics",
            "javascript framework",
        ])
        s.add_tags(["python", "javascript", "web", "data-science"])
        s.add_keywords(["python", "async", "web", "machine-learning"])
        return s

    # ── suggest() tests ───────────────────────────────────────────

    def test_suggest_min_prefix_length_filter(self, suggestions: SearchSuggestions) -> None:
        """Prefix shorter than min_prefix_length returns no results."""
        results = suggestions.suggest("p")
        assert len(results) == 0

    def test_suggest_from_history(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("pyt", sources=["history"])
        assert len(results) > 0
        assert all(r.source == "history" for r in results)

    def test_suggest_from_tags(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("jav", sources=["tags"])
        assert len(results) > 0
        assert all(r.source == "tags" for r in results)

    def test_suggest_from_keywords(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("pyt", sources=["keywords"])
        assert len(results) > 0
        assert all(r.source == "keywords" for r in results)

    def test_suggest_from_trending(self, suggestions: SearchSuggestions) -> None:
        suggestions.record_search("python")
        suggestions.record_search("python")
        results = suggestions.suggest("pyt", sources=["trending"])
        trending_results = [r for r in results if r.source == "trending"]
        assert len(trending_results) > 0


    def test_suggest_from_trending_mixed_case(self, suggestions: SearchSuggestions) -> None:
        """A mixed-case trending query is returned for a lowercase prefix (TICKET-283)."""
        s = SearchSuggestions(max_suggestions=10, min_prefix_length=2)
        s.record_search("Python")
        s.record_search("Python")
        results = s.suggest("py", sources=["trending"])
        trending_results = [r for r in results if r.source == "trending"]
        assert len(trending_results) > 0
        assert any(r.text == "Python" for r in trending_results)

    def test_suggest_from_trending_mixed_case_full_prefix(self) -> None:
        """A mixed-case trending query matches its own lowercased full prefix (TICKET-283)."""
        s = SearchSuggestions(max_suggestions=10, min_prefix_length=2)
        s.record_search("Python")
        results = s.suggest("python", sources=["trending"])
        trending_results = [r for r in results if r.source == "trending"]
        assert any(r.text == "Python" for r in trending_results)

    def test_suggest_from_trending_lowercase_still_works(self) -> None:
        """Lowercase trending queries still match (no regression from TICKET-283)."""
        s = SearchSuggestions(max_suggestions=10, min_prefix_length=2)
        s.record_search("python")
        results = s.suggest("py", sources=["trending"])
        trending_results = [r for r in results if r.source == "trending"]
        assert any(r.text == "python" for r in trending_results)

    def test_suggest_fuzzy_true(self, suggestions: SearchSuggestions) -> None:
        """Fuzzy=True should return at least as many results as fuzzy=False."""
        exact = suggestions.suggest("pyt", fuzzy=False)
        fuzzy = suggestions.suggest("pyt", fuzzy=True)
        assert len(fuzzy) >= len(exact)

    def test_suggest_fuzzy_false(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("pyt", fuzzy=False)
        # All results should start with the prefix (exact/prefix match)
        for r in results:
            if r.source in ("history", "tags", "keywords", "trending"):
                assert r.text.lower().startswith("pyt")

    def test_suggest_max_suggestions_limit(self) -> None:
        s = SearchSuggestions(max_suggestions=3)
        s.add_search_history([
            "apple", "application", "apply", "appetite", "appreciate",
        ])
        results = s.suggest("app")
        assert len(results) <= 3

    def test_suggest_all_sources(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("pyt")
        sources = {r.source for r in results}
        assert "history" in sources

    def test_suggest_empty_prefix(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("")
        assert len(results) == 0

    def test_suggest_no_matches(self, suggestions: SearchSuggestions) -> None:
        results = suggestions.suggest("zzzzz")
        assert len(results) == 0

    # ── record_search / get_trending tests ────────────────────────

    def test_record_search_adds_to_history(self, suggestions: SearchSuggestions) -> None:
        before = len(suggestions._search_history)
        suggestions.record_search("new query")
        assert len(suggestions._search_history) == before + 1

    def test_record_search_creates_trending_entry(self, suggestions: SearchSuggestions) -> None:
        suggestions.record_search("python")
        assert "python" in suggestions._trending

    def test_record_search_increments_existing_trending(self, suggestions: SearchSuggestions) -> None:
        suggestions.record_search("python")
        suggestions.record_search("python")
        entry = suggestions._trending["python"]
        assert entry.count == 2

    def test_get_trending_returns_sorted_by_decayed_score(self) -> None:
        s = SearchSuggestions()
        s.record_search("a")
        s.record_search("b")
        s.record_search("b")
        trending = s.get_trending()
        assert trending[0] == "b"

    def test_get_trending_with_decay(self) -> None:
        s = SearchSuggestions(decay_half_life=1.0)
        s.record_search("old_query")
        time.sleep(0.05)
        s.record_search("new_query")
        trending = s.get_trending()
        assert trending[0] == "new_query"

    def test_get_trending_respects_n_limit(self) -> None:
        s = SearchSuggestions()
        for i in range(20):
            s.record_search(f"query_{i}")
        trending = s.get_trending(n=5)
        assert len(trending) == 5

    def test_get_trending_empty(self) -> None:
        s = SearchSuggestions()
        assert s.get_trending() == []

    # ── get_related_queries tests ─────────────────────────────────

    def test_get_related_queries_word_overlap(self) -> None:
        s = SearchSuggestions()
        s.add_search_history([
            "python web framework",
            "python data analysis",
            "javascript web",
            "ruby basics",
        ])
        related = s.get_related_queries("python web")
        assert len(related) > 0
        # "python data analysis" shares "python"
        # "javascript web" shares "web"
        texts = [r.text for r in related]
        assert "python data analysis" in texts or "javascript web" in texts

    def test_get_related_queries_excludes_self(self) -> None:
        s = SearchSuggestions()
        s.add_search_history(["python web", "python data"])
        related = s.get_related_queries("python web")
        texts = [r.text for r in related]
        assert "python web" not in texts

    def test_get_related_queries_no_match(self) -> None:
        s = SearchSuggestions()
        s.add_search_history(["python", "javascript"])
        related = s.get_related_queries("xyznonexistent")
        assert len(related) == 0

    def test_get_related_queries_respects_n_limit(self) -> None:
        s = SearchSuggestions()
        for i in range(20):
            s.add_search_history([f"shared word {i}"])
        related = s.get_related_queries("shared word", n=3)
        assert len(related) <= 3

    # ── clear / to_dict / from_dict tests ─────────────────────────

    def test_clear_removes_all_data(self, suggestions: SearchSuggestions) -> None:
        suggestions.record_search("python")
        suggestions.clear()
        assert len(suggestions._search_history) == 0
        assert len(suggestions._tags) == 0
        assert len(suggestions._keywords) == 0
        assert len(suggestions._trending) == 0

    def test_to_dict_contains_all_fields(self, suggestions: SearchSuggestions) -> None:
        data = suggestions.to_dict()
        assert "search_history" in data
        assert "tags" in data
        assert "keywords" in data
        assert "trending" in data

    def test_from_dict_roundtrip(self, suggestions: SearchSuggestions) -> None:
        suggestions.record_search("python")
        data = suggestions.to_dict()
        restored = SearchSuggestions.from_dict(data)
        assert restored._search_history == suggestions._search_history
        assert restored._tags == suggestions._tags
        assert restored._keywords == suggestions._keywords
        assert len(restored._trending) == len(suggestions._trending)

    def test_from_dict_empty_data(self) -> None:
        restored = SearchSuggestions.from_dict({})
        assert restored._search_history == []
        assert restored._tags == []
        assert restored._keywords == []
        assert restored._trending == {}

    def test_from_dict_backward_compat_trending(self) -> None:
        """Old format: trending was {query: count}."""
        data = {
            "search_history": [],
            "tags": [],
            "keywords": [],
            "trending": {"python": 5, "java": 3},
        }
        restored = SearchSuggestions.from_dict(data)
        assert "python" in restored._trending
        assert restored._trending["python"].count == 5

    def test_to_dict_returns_copies_not_live_lists(self, suggestions: SearchSuggestions) -> None:
        """Mutating the dict returned by to_dict must not change the instance."""
        suggestions._search_history.append("query1")
        suggestions._tags.append("tag1")
        suggestions._keywords.append("kw1")
        d = suggestions.to_dict()
        d["search_history"].append("hacked")
        d["tags"].append("hacked")
        d["keywords"].append("hacked")
        assert "hacked" not in suggestions._search_history
        assert "hacked" not in suggestions._tags
        assert "hacked" not in suggestions._keywords

    def test_from_dict_does_not_alias_input_lists(self) -> None:
        """Mutating the input dict after from_dict must not change the instance."""
        data = {
            "search_history": ["a", "b"],
            "tags": ["x"],
            "keywords": ["y"],
        }
        inst = SearchSuggestions.from_dict(data)
        data["search_history"].append("c")
        data["tags"].append("z")
        data["keywords"].append("w")
        assert inst._search_history == ["a", "b"]
        assert inst._tags == ["x"]
        assert inst._keywords == ["y"]
