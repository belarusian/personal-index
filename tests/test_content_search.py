"""Tests for content_search module."""

import pytest
from datetime import datetime, timezone
from personal_index.content_search import SearchIndex, ContentSearch


@pytest.fixture
def sample_items():
    return [
        {"id": "1", "title": "Python Tutorial", "description": "Learn Python basics", "tags": ["python", "tutorial"]},
        {"id": "2", "title": "JavaScript Guide", "description": "JavaScript fundamentals", "tags": ["javascript", "web"]},
        {"id": "3", "title": "Python Advanced", "description": "Advanced Python techniques", "tags": ["python", "advanced"]},
        {"id": "4", "title": "React Framework", "description": "Building UIs with React", "tags": ["react", "javascript", "web"]},
        {"id": "5", "title": "Data Science", "description": "Python for data science", "tags": ["python", "data"]},
    ]


@pytest.fixture
def search():
    s = ContentSearch()
    return s


# --- Basic Indexing Tests ---

class TestIndexing:
    def test_add_single_item(self, search):
        search.index_items([{"id": "1", "title": "Test Post"}])
        assert search.index.item_count == 1

    def test_add_multiple_items(self, search, sample_items):
        search.index_items(sample_items)
        assert search.index.item_count == 5

    def test_remove_item(self, search, sample_items):
        search.index_items(sample_items)
        search.remove_item("1")
        assert search.index.item_count == 4

    def test_remove_nonexistent_item(self, search):
        search.remove_item("999")  # should not raise

    def test_term_count(self, search, sample_items):
        search.index_items(sample_items)
        assert search.index.term_count > 0

    def test_add_duplicate_item(self, search):
        item = {"id": "1", "title": "Test"}
        search.index_items([item, item])
        assert search.index.item_count == 1


# --- Search Tests ---

class TestSearch:
    def test_search_basic(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        assert result["total"] > 0
        assert result["query"] == "python"

    def test_search_returns_results(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        assert len(result["results"]) > 0
        assert "item" in result["results"][0]
        assert "score" in result["results"][0]

    def test_search_no_results(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("xyznonexistent")
        assert result["total"] == 0
        assert result["results"] == []

    def test_search_empty_query(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("")
        assert result["total"] == 0

    def test_search_ranking(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_multi_word(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python tutorial")
        assert result["total"] > 0

    def test_search_pagination(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python", limit=2)
        assert len(result["results"]) <= 2

    def test_search_offset(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python", limit=2, offset=1)
        assert len(result["results"]) <= 2

    def test_search_score_positive(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        for r in result["results"]:
            assert r["score"] > 0


# --- Filter Tests ---

class TestFilters:
    def test_filter_by_tag(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python", filters={"tags": ["python", "tutorial"]})
        for r in result["results"]:
            assert "python" in r["item"].get("tags", []) or "tutorial" in r["item"].get("tags", [])

    def test_filter_by_exact_field(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("javascript", filters={"tags": ["javascript", "web"]})
        assert result["total"] > 0

    def test_filter_excludes(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python", filters={"tags": ["react"]})
        assert result["total"] == 0

    def test_filter_range_gte(self, search):
        items = [
            {"id": "1", "title": "Old", "date": datetime(2023, 1, 1)},
            {"id": "2", "title": "New", "date": datetime(2024, 6, 1)},
        ]
        search.index_items(items)
        result = search.search("old", filters={"date": {"$gte": datetime(2024, 1, 1)}})
        assert result["total"] == 0

    def test_filter_range_lte(self, search):
        items = [
            {"id": "1", "title": "Old", "date": datetime(2023, 1, 1)},
            {"id": "2", "title": "New", "date": datetime(2024, 6, 1)},
        ]
        search.index_items(items)
        result = search.search("old", filters={"date": {"$lte": datetime(2023, 6, 1)}})
        assert result["total"] == 1


# --- Suggestions Tests ---

class TestSuggestions:
    def test_suggestions_basic(self, search, sample_items):
        search.index_items(sample_items)
        suggestions = search.get_suggestions("pyt")
        assert "python" in suggestions

    def test_suggestions_limit(self, search, sample_items):
        search.index_items(sample_items)
        suggestions = search.get_suggestions("", limit=3)
        assert len(suggestions) <= 3

    def test_suggestions_empty(self, search, sample_items):
        search.index_items(sample_items)
        suggestions = search.get_suggestions("zzz")
        assert suggestions == []


# --- Edge Cases ---

class TestEdgeCases:
    def test_search_stop_words(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("the is a")
        assert result["total"] == 0

    def test_search_case_insensitive(self, search, sample_items):
        search.index_items(sample_items)
        r1 = search.search("Python")
        r2 = search.search("python")
        assert r1["total"] == r2["total"]

    def test_search_special_chars(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python!")
        assert result["total"] > 0

    def test_index_empty_items(self, search):
        search.index_items([])
        assert search.index.item_count == 0

    def test_search_empty_index(self, search):
        result = search.search("anything")
        assert result["total"] == 0

    def test_remove_and_search(self, search, sample_items):
        search.index_items(sample_items)
        search.remove_item("1")
        result = search.search("tutorial")
        # Item 1 had "tutorial" in tags, so removing it should reduce results
        ids = [r["item"]["id"] for r in result["results"]]
        assert "1" not in ids


# --- Additional Search Tests ---

class TestSearchAdvanced:
    def test_search_partial_match(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("pyth")
        assert result["total"] > 0

    def test_search_tags_indexed(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("tutorial")
        assert result["total"] > 0

    def test_search_description_only(self, search):
        items = [{"id": "1", "title": "X", "description": "find me here"}]
        search.index_items(items)
        result = search.search("find me")
        assert result["total"] == 1

    def test_search_result_structure(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        for r in result["results"]:
            assert "item" in r
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_search_total_matches(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python")
        assert result["total"] == len(result["results"])

    def test_search_limit_respected(self, search, sample_items):
        search.index_items(sample_items)
        result = search.search("python", limit=1)
        assert len(result["results"]) == 1
        assert result["total"] >= 1

    def test_search_offset_pagination(self, search, sample_items):
        search.index_items(sample_items)
        r1 = search.search("python", limit=1, offset=0)
        r2 = search.search("python", limit=1, offset=1)
        if r2["total"] > 1:
            assert r1["results"][0]["item"]["id"] != r2["results"][0]["item"]["id"]


# --- Index Persistence Tests ---

class TestIndexPersistence:
    def test_save_and_load_index(self, search, sample_items, tmp_path):
        search.index_items(sample_items)
        filepath = tmp_path / "index.json"
        search.index.save_index(str(filepath))
        new_search = ContentSearch()
        new_search.index.load_index(str(filepath))
        assert new_search.index.item_count == 5
        result = new_search.search("python")
        assert result["total"] > 0

    def test_save_index_creates_file(self, search, sample_items, tmp_path):
        search.index_items(sample_items)
        filepath = tmp_path / "index.json"
        search.index.save_index(str(filepath))
        assert filepath.exists()

    def test_load_empty_index(self, search, tmp_path):
        search.index.save_index(str(tmp_path / "empty.json"))
        new_search = ContentSearch()
        new_search.index.load_index(str(tmp_path / "empty.json"))
        assert new_search.index.item_count == 0


# --- Highlight Tests ---

class TestHighlight:
    def test_highlight_basic(self, search):
        text = "Python is great for Python programming"
        result = search.index.highlight_matches(text, "python")
        assert "*" in result

    def test_highlight_case_insensitive(self, search):
        text = "PYTHON is great"
        result = search.index.highlight_matches(text, "python")
        assert "*python*" in result.lower() or "*PYTHON*" in result

    def test_highlight_multiple_terms(self, search):
        text = "Python JavaScript both are languages"
        result = search.index.highlight_matches(text, "python javascript")
        assert "*" in result

    def test_highlight_no_match(self, search):
        text = "No matching terms here"
        result = search.index.highlight_matches(text, "xyz")
        assert result == text
