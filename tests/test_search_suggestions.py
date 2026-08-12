"""Tests for search suggestions module."""

from personal_index.search_suggestions import SearchSuggestions, Suggestion


class TestSuggestion:
    def test_default_values(self):
        s = Suggestion(text="python")
        assert s.text == "python"
        assert s.score == 0.0
        assert s.source == "unknown"

    def test_to_dict(self):
        s = Suggestion(text="python", score=0.8, source="history")
        d = s.to_dict()
        assert d["text"] == "python"
        assert d["score"] == 0.8
        assert d["source"] == "history"


class TestSearchSuggestions:
    def setup_method(self):
        self.suggestions = SearchSuggestions(max_suggestions=5)
        self.suggestions.add_search_history([
            "python tutorial", "python web", "python data",
            "javascript basics", "javascript framework",
            "python tutorial",  # repeated
        ])
        self.suggestions.add_tags(["python", "javascript", "web", "data-science", "ml"])
        self.suggestions.add_keywords(["python", "async", "web", "machine-learning", "data"])

    def test_suggest_from_history(self):
        results = self.suggestions.suggest("pyt")
        assert len(results) > 0
        assert all(r.text.startswith("pyt") for r in results)
        assert any(r.source == "history" for r in results)

    def test_suggest_from_tags(self):
        results = self.suggestions.suggest("jav", sources=["tags"])
        assert len(results) > 0
        assert all(r.source == "tags" for r in results)

    def test_suggest_from_keywords(self):
        results = self.suggestions.suggest("dat", sources=["keywords"])
        assert len(results) > 0
        assert all(r.source == "keywords" for r in results)

    def test_suggest_min_prefix(self):
        results = self.suggestions.suggest("p")
        assert len(results) == 0

    def test_suggest_max_results(self):
        results = self.suggestions.suggest("p")
        assert len(results) <= self.suggestions.max_suggestions

    def test_suggest_empty(self):
        empty = SearchSuggestions()
        results = empty.suggest("xyz")
        assert len(results) == 0

    def test_record_search(self):
        self.suggestions.record_search("python")
        self.suggestions.record_search("python")
        self.suggestions.record_search("java")
        trending = self.suggestions.get_trending()
        assert trending[0] == "python"

    def test_get_trending(self):
        self.suggestions.record_search("a")
        self.suggestions.record_search("b")
        self.suggestions.record_search("b")
        trending = self.suggestions.get_trending(n=1)
        assert trending == ["b"]

    def test_get_trending_limit(self):
        for i in range(20):
            self.suggestions.record_search(f"query_{i}")
        trending = self.suggestions.get_trending(n=5)
        assert len(trending) == 5

    def test_related_queries(self):
        self.suggestions.add_search_history([
            "python web framework",
            "python data analysis",
            "javascript web",
            "ruby basics",
        ])
        related = self.suggestions.get_related_queries("python web")
        assert len(related) > 0
        assert all(r.source == "related" for r in related)

    def test_related_no_match(self):
        related = self.suggestions.get_related_queries("xyznonexistent")
        assert len(related) == 0

    def test_clear(self):
        self.suggestions.clear()
        assert len(self.suggestions.suggest("pyt")) == 0

    def test_serialization_roundtrip(self):
        data = self.suggestions.to_dict()
        restored = SearchSuggestions.from_dict(data)
        assert restored._search_history == self.suggestions._search_history
        assert restored._tags == self.suggestions._tags

    def test_suggest_multiple_sources(self):
        results = self.suggestions.suggest("pyt", sources=["history", "tags", "keywords"])
        sources_found = {r.source for r in results}
        assert "history" in sources_found or "tags" in sources_found or "keywords" in sources_found

    def test_suggest_case_insensitive(self):
        results = self.suggestions.suggest("PYT")
        assert len(results) > 0

    def test_trending_boost(self):
        s = SearchSuggestions()
        s.record_search("python")
        s.record_search("python")
        s.record_search("python")
        s.add_keywords(["python"])
        results = s.suggest("pyt")
        trending_results = [r for r in results if r.source == "trending"]
        assert len(trending_results) > 0
