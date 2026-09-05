"""Tests for personal_index.content_search module.

Covers:
- Snippet dataclass and to_dict()
- SnippetExtractor.extract()
- SearchIndex.add_item(), add_items(), item_count, term_count
- SearchIndex.search()
- SearchIndex.remove_item()
- SearchIndex.get_suggestions()
- SearchIndex.save_index() / load_index()
- SearchIndex.highlight_matches()
- ContentSearch.index_items(), search(), remove_item(), get_suggestions()
"""

from __future__ import annotations

import pytest

from personal_index.content_search import (
    ContentSearch,
    SearchIndex,
    Snippet,
    SnippetExtractor,
)

# ---------------------------------------------------------------------------
# Snippet dataclass tests
# ---------------------------------------------------------------------------


class TestSnippet:
    """Tests for Snippet dataclass."""

    def test_snippet_creation(self):
        s = Snippet(text="hello world", highlighted="<mark>hello</mark> world")
        assert s.text == "hello world"
        assert s.highlighted == "<mark>hello</mark> world"
        assert s.start_offset == 0
        assert s.end_offset == 0
        assert s.matched_terms == []

    def test_snippet_with_offsets(self):
        s = Snippet(
            text="hello world",
            highlighted="<mark>hello</mark> world",
            start_offset=5,
            end_offset=15,
            matched_terms=["hello"],
        )
        assert s.start_offset == 5
        assert s.end_offset == 15
        assert s.matched_terms == ["hello"]

    def test_snippet_to_dict(self):
        s = Snippet(
            text="hello world",
            highlighted="<mark>hello</mark> world",
            start_offset=5,
            end_offset=15,
            matched_terms=["hello"],
        )
        d = s.to_dict()
        assert d["text"] == "hello world"
        assert d["highlighted"] == "<mark>hello</mark> world"
        assert d["start_offset"] == 5
        assert d["end_offset"] == 15
        assert d["matched_terms"] == ["hello"]


# ---------------------------------------------------------------------------
# SnippetExtractor tests
# ---------------------------------------------------------------------------


class TestSnippetExtractor:
    """Tests for SnippetExtractor."""

    @pytest.fixture
    def extractor(self):
        return SnippetExtractor(max_snippet_length=100, max_snippets=3)

    def test_extract_single_match(self, extractor):
        text = "The quick brown fox jumps over the lazy dog"
        snippets = extractor.extract(text, ["fox"])
        assert len(snippets) == 1
        assert "fox" in snippets[0].text.lower()

    def test_extract_multiple_matches(self, extractor):
        text = "Python is great. Python is popular. Python is fun."
        snippets = extractor.extract(text, ["python"])
        assert len(snippets) >= 1

    def test_extract_no_match(self, extractor):
        text = "The quick brown fox"
        snippets = extractor.extract(text, ["xyz"])
        # Returns fallback snippet when no match
        assert len(snippets) == 1

    def test_extract_highlights_terms(self, extractor):
        text = "Python programming is fun"
        snippets = extractor.extract(text, ["python"])
        assert len(snippets) >= 1
        assert "<mark>" in snippets[0].highlighted

    def test_extract_empty_text(self, extractor):
        snippets = extractor.extract("", ["python"])
        assert snippets == []

    def test_extract_empty_query(self, extractor):
        snippets = extractor.extract("some text", [])
        assert snippets == []

    def test_extract_max_snippets_limit(self):
        extractor = SnippetExtractor(max_snippets=2)
        text = "A A A A A A A A A A A A A A A"
        snippets = extractor.extract(text, ["A"])
        assert len(snippets) <= 2

    def test_extract_matched_terms(self, extractor):
        text = "Python and JavaScript are languages"
        snippets = extractor.extract(text, ["python", "javascript"])
        assert len(snippets) >= 1
        assert "python" in snippets[0].matched_terms or "javascript" in snippets[0].matched_terms


# ---------------------------------------------------------------------------
# SearchIndex tests
# ---------------------------------------------------------------------------


class TestSearchIndex:
    """Tests for SearchIndex."""

    @pytest.fixture
    def index(self):
        return SearchIndex()

    def test_add_item(self, index):
        index.add_item({"id": "1", "title": "Python Tutorial", "description": "Learn Python"})
        assert index.item_count == 1

    def test_add_items(self, index):
        items = [
            {"id": "1", "title": "Python Tutorial"},
            {"id": "2", "title": "JavaScript Guide"},
        ]
        index.add_items(items)
        assert index.item_count == 2

    def test_item_count(self, index):
        assert index.item_count == 0
        index.add_item({"id": "1", "title": "Test"})
        assert index.item_count == 1

    def test_term_count(self, index):
        index.add_item({"id": "1", "title": "Python Tutorial", "description": "Learn Python basics"})
        assert index.term_count > 0

    def test_search_keyword_match(self, index):
        index.add_items([
            {"id": "1", "title": "Python Tutorial", "description": "Learn Python"},
            {"id": "2", "title": "JavaScript Guide", "description": "Learn JavaScript"},
        ])
        result = index.search("python")
        assert result["total"] > 0
        assert result["query"] == "python"

    def test_search_empty_query(self, index):
        index.add_item({"id": "1", "title": "Test"})
        result = index.search("")
        assert result["total"] == 0

    def test_search_filter_by_category(self, index):
        index.add_items([
            {"id": "1", "title": "Python", "category": "tech"},
            {"id": "2", "title": "Recipe", "category": "food"},
        ])
        result = index.search("python", filters={"category": "tech"})
        assert result["total"] > 0

    def test_search_filter_by_source(self, index):
        index.add_items([
            {"id": "1", "title": "Python", "source": "blog"},
            {"id": "2", "title": "Recipe", "source": "cookbook"},
        ])
        result = index.search("python", filters={"source": "blog"})
        assert result["total"] > 0

    def test_search_filter_by_domain(self, index):
        index.add_items([
            {"id": "1", "title": "Python", "domain": "example.com"},
            {"id": "2", "title": "Recipe", "domain": "food.com"},
        ])
        result = index.search("python", filters={"domain": "example.com"})
        assert result["total"] > 0

    def test_remove_item(self, index):
        index.add_items([
            {"id": "1", "title": "Python"},
            {"id": "2", "title": "JavaScript"},
        ])
        assert index.item_count == 2
        index.remove_item("1")
        assert index.item_count == 1

    def test_remove_nonexistent_item(self, index):
        index.remove_item("nonexistent")  # Should not raise

    def test_get_suggestions_prefix(self, index):
        index.add_items([
            {"id": "1", "title": "Python Tutorial"},
            {"id": "2", "title": "Python Advanced"},
            {"id": "3", "title": "JavaScript Guide"},
        ])
        suggestions = index.get_suggestions("python")
        assert "python" in suggestions

    def test_get_suggestions_limit(self, index):
        index.add_items([
            {"id": str(i), "title": f"Alpha {i}"} for i in range(10)
        ])
        suggestions = index.get_suggestions("alpha", limit=3)
        assert len(suggestions) <= 3

    def test_get_suggestions_no_match(self, index):
        index.add_item({"id": "1", "title": "Python"})
        suggestions = index.get_suggestions("zzz")
        assert suggestions == []

    def test_save_and_load_index(self, index, tmp_path):
        items = [
            {"id": "1", "title": "Python Tutorial", "description": "Learn Python"},
            {"id": "2", "title": "JavaScript Guide"},
        ]
        index.add_items(items)
        filepath = str(tmp_path / "index.json")
        index.save_index(filepath)

        new_index = SearchIndex()
        new_index.load_index(filepath)
        assert new_index.item_count == 2
        result = new_index.search("python")
        assert result["total"] > 0

    def test_save_index_creates_file(self, index, tmp_path):
        index.add_item({"id": "1", "title": "Test"})
        filepath = str(tmp_path / "index.json")
        index.save_index(filepath)
        assert tmp_path.joinpath("index.json").exists()

    def test_load_empty_index(self, index, tmp_path):
        filepath = str(tmp_path / "empty.json")
        index.save_index(filepath)
        new_index = SearchIndex()
        new_index.load_index(filepath)
        assert new_index.item_count == 0

    def test_highlight_matches(self, index):
        text = "Python is great for Python programming"
        result = index.highlight_matches(text, "python")
        assert "*" in result

    def test_highlight_matches_case_insensitive(self, index):
        text = "PYTHON is great"
        result = index.highlight_matches(text, "python")
        assert "*" in result.lower()

    def test_highlight_matches_no_match(self, index):
        text = "No matching terms here"
        result = index.highlight_matches(text, "xyz")
        assert result == text

    def test_highlight_matches_multiple_terms(self, index):
        text = "Python JavaScript both are languages"
        result = index.highlight_matches(text, "python javascript")
        assert "*" in result

    def test_search_no_results(self, index):
        index.add_item({"id": "1", "title": "Python"})
        result = index.search("xyznonexistent")
        assert result["total"] == 0

    def test_search_results_sorted_by_score(self, index):
        index.add_items([
            {"id": "1", "title": "Python", "description": "Python Python Python"},
            {"id": "2", "title": "Python Tutorial", "description": "Python"},
        ])
        result = index.search("python")
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_limit(self, index):
        index.add_items([
            {"id": str(i), "title": "Python Tutorial"} for i in range(5)
        ])
        result = index.search("python", limit=2)
        assert len(result["results"]) <= 2

    def test_search_offset(self, index):
        index.add_items([
            {"id": str(i), "title": "Python Tutorial"} for i in range(5)
        ])
        r1 = index.search("python", limit=2, offset=0)
        r2 = index.search("python", limit=2, offset=2)
        if len(r1["results"]) > 0 and len(r2["results"]) > 0:
            assert r1["results"][0]["item"]["id"] != r2["results"][0]["item"]["id"]

    def test_search_returns_exact_fields_normal_and_guard(self, index):
        # Normal case: 5 matching items, page sliced to limit=2.
        index.add_items([
            {"id": str(i), "title": "Python Tutorial",
             "description": "Learn Python", "content": "python body"}
            for i in range(5)
        ])
        result = index.search("python", limit=2)
        # query echoed back unchanged
        assert result["query"] == "python"
        # total = ALL ranked candidates BEFORE the page slice (5), not the page len (2)
        assert result["total"] == 5
        assert len(result["results"]) == 2
        # each entry: exactly {item, score}; content key stripped; score rounded to 4
        for entry in result["results"]:
            assert set(entry.keys()) == {"item", "score"}
            assert "content" not in entry["item"]
            assert entry["item"]["id"] in {str(i) for i in range(5)}
            assert isinstance(entry["score"], float)
            assert entry["score"] == round(entry["score"], 4)
        # highlight=True adds a "snippets" key with 5-field snippet dicts
        hl = index.search("python", limit=2, highlight=True)
        for entry in hl["results"]:
            assert set(entry.keys()) == {"item", "score", "snippets"}
            assert entry["snippets"]
            for snip in entry["snippets"]:
                assert set(snip.keys()) == {
                    "text", "highlighted", "start_offset", "end_offset", "matched_terms",
                }
        # Guard path: stop-word-only query tokenizes to nothing -> exact empty dict
        guard = index.search("the and of")
        assert guard == {"results": [], "total": 0, "query": "the and of"}


class TestSearchIndexLoadNonDictGuard:
    """Regression: non-dict JSON in index file must not crash SearchIndex.load_index."""

    def test_load_null_json(self, tmp_path):
        filepath = str(tmp_path / "idx.json")
        with open(filepath, "w") as f:
            f.write("null")
        idx = SearchIndex()
        idx.load_index(filepath)
        assert idx.item_count == 0
        assert idx.term_count == 0

    def test_load_list_json(self, tmp_path):
        filepath = str(tmp_path / "idx.json")
        with open(filepath, "w") as f:
            f.write("[1, 2, 3]")
        idx = SearchIndex()
        idx.load_index(filepath)
        assert idx.item_count == 0
        assert idx.term_count == 0

    def test_load_number_json(self, tmp_path):
        filepath = str(tmp_path / "idx.json")
        with open(filepath, "w") as f:
            f.write("42")
        idx = SearchIndex()
        idx.load_index(filepath)
        assert idx.item_count == 0
        assert idx.term_count == 0

class TestSearchIndexLoadCorruptJsonGuard:
    """Regression: corrupt/truncated JSON in index file must not crash SearchIndex.load_index."""

    def test_load_corrupt_brace_json(self, tmp_path):
        filepath = str(tmp_path / "idx.json")
        with open(filepath, "w") as f:
            f.write("{")
        idx = SearchIndex()
        idx.load_index(filepath)
        assert idx.item_count == 0
        assert idx.term_count == 0

    def test_load_truncated_json(self, tmp_path):
        filepath = str(tmp_path / "idx.json")
        with open(filepath, "w") as f:
            f.write('{"items": {"1": {"title": "http://exa')
        idx = SearchIndex()
        idx.load_index(filepath)
        assert idx.item_count == 0
        assert idx.term_count == 0



# ---------------------------------------------------------------------------
# ContentSearch tests
# ---------------------------------------------------------------------------


class TestContentSearch:
    """Tests for ContentSearch high-level interface."""

    @pytest.fixture
    def search(self):
        return ContentSearch()

    def test_index_items(self, search):
        items = [
            {"id": "1", "title": "Python Tutorial"},
            {"id": "2", "title": "JavaScript Guide"},
        ]
        search.index_items(items)
        assert search.index.item_count == 2

    def test_search(self, search):
        search.index_items([
            {"id": "1", "title": "Python Tutorial", "description": "Learn Python"},
        ])
        result = search.search("python")
        assert result["total"] > 0
        assert result["query"] == "python"

    def test_search_with_filters(self, search):
        search.index_items([
            {"id": "1", "title": "Python", "category": "tech"},
        ])
        result = search.search("python", filters={"category": "tech"})
        assert result["total"] > 0

    def test_remove_item(self, search):
        search.index_items([
            {"id": "1", "title": "Python"},
            {"id": "2", "title": "JavaScript"},
        ])
        search.remove_item("1")
        assert search.index.item_count == 1

    def test_get_suggestions(self, search):
        search.index_items([
            {"id": "1", "title": "Python Tutorial"},
            {"id": "2", "title": "Python Advanced"},
        ])
        suggestions = search.get_suggestions("python")
        assert "python" in suggestions

    def test_get_suggestions_limit(self, search):
        search.index_items([
            {"id": str(i), "title": f"Alpha {i}"} for i in range(10)
        ])
        suggestions = search.get_suggestions("alpha", limit=3)
        assert len(suggestions) <= 3

    def test_search_empty_index(self, search):
        result = search.search("anything")
        assert result["total"] == 0

    def test_search_empty_query(self, search):
        search.index_items([{"id": "1", "title": "Test"}])
        result = search.search("")
        assert result["total"] == 0
