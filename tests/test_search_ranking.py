"""Tests for TF-IDF and BM25 ranking in content search."""

from __future__ import annotations

from personal_index.content_search import ContentSearch, SearchIndex, Snippet, SnippetExtractor


class TestTFIDFRanking:
    """Tests for TF-IDF ranking algorithm."""

    def setup_method(self):
        self.index = SearchIndex()

    def test_tfidf_basic(self):
        """TF-IDF should rank documents by term frequency * inverse document frequency."""
        self.index.add_item({"id": "1", "title": "Python programming", "content": "Python is great for programming"})
        self.index.add_item({"id": "2", "title": "Java programming", "content": "Java is also great for programming"})
        self.index.add_item({"id": "3", "title": "Python tutorial", "content": "Learn Python basics"})

        results = self.index.search("python", ranking="tfidf")
        assert len(results["results"]) == 2
        # Both docs 1 and 3 contain "python"
        result_ids = [r["item"]["id"] for r in results["results"]]
        assert "1" in result_ids
        assert "3" in result_ids

    def test_tfidf_idf_effect(self):
        """Rare terms should get higher IDF scores."""
        self.index.add_item({"id": "1", "title": "Python tutorial", "content": "Python basics"})
        self.index.add_item({"id": "2", "title": "Python advanced", "content": "Python advanced"})
        self.index.add_item({"id": "3", "title": "Rust tutorial", "content": "Rust basics"})

        results = self.index.search("rust", ranking="tfidf")
        assert len(results["results"]) == 1
        assert results["results"][0]["item"]["id"] == "3"

    def test_tfidf_normalized_tf(self):
        """TF should be normalized by document length."""
        self.index.add_item({"id": "1", "title": "Python", "content": "Python"})
        self.index.add_item({"id": "2", "title": "Long doc", "content": "This is a very long document about python and many other things"})

        results = self.index.search("python", ranking="tfidf")
        assert len(results["results"]) == 2
        # Both should match
        result_ids = [r["item"]["id"] for r in results["results"]]
        assert "1" in result_ids
        assert "2" in result_ids

    def test_tfidf_empty_index(self):
        results = self.index.search("test", ranking="tfidf")
        assert results["results"] == []

    def test_tfidf_no_match(self):
        self.index.add_item({"id": "1", "title": "Hello world"})
        results = self.index.search("xyz", ranking="tfidf")
        assert results["results"] == []


class TestBM25Ranking:
    """Tests for BM25 ranking algorithm."""

    def setup_method(self):
        self.index = SearchIndex()

    def test_bm25_basic(self):
        """BM25 should rank documents by relevance."""
        self.index.add_item({"id": "1", "title": "Python programming", "content": "Python is great for programming"})
        self.index.add_item({"id": "2", "title": "Java programming", "content": "Java is also great for programming"})
        self.index.add_item({"id": "3", "title": "Python tutorial", "content": "Learn Python basics"})

        results = self.index.search("python", ranking="bm25")
        assert len(results["results"]) == 2
        result_ids = [r["item"]["id"] for r in results["results"]]
        assert "1" in result_ids
        assert "3" in result_ids

    def test_bm25_saturation(self):
        """BM25 should saturate TF (diminishing returns for repeated terms)."""
        self.index.add_item({"id": "1", "title": "Python", "content": "Python Python Python Python Python Python"})
        self.index.add_item({"id": "2", "title": "Python", "content": "Python"})

        results = self.index.search("python", ranking="bm25")
        assert len(results["results"]) == 2
        # Both should match, but doc 1 shouldn't be infinitely better
        assert results["results"][0]["score"] > results["results"][1]["score"]

    def test_bm25_length_normalization(self):
        """BM25 should penalize longer documents."""
        self.index.add_item({"id": "1", "title": "Python", "content": "Python"})
        self.index.add_item({"id": "2", "title": "Long", "content": "This is a very long document with many words about python and other topics"})

        results = self.index.search("python", ranking="bm25")
        assert len(results["results"]) == 2
        result_ids = [r["item"]["id"] for r in results["results"]]
        assert "1" in result_ids
        assert "2" in result_ids

    def test_bm25_empty_index(self):
        results = self.index.search("test", ranking="bm25")
        assert results["results"] == []

    def test_bm25_no_match(self):
        self.index.add_item({"id": "1", "title": "Hello world"})
        results = self.index.search("xyz", ranking="bm25")
        assert results["results"] == []


class TestRankingComparison:
    """Compare different ranking algorithms."""

    def setup_method(self):
        self.index = SearchIndex()
        self.index.add_item({"id": "1", "title": "Python programming", "content": "Python is great for programming"})
        self.index.add_item({"id": "2", "title": "Java programming", "content": "Java is also great for programming"})
        self.index.add_item({"id": "3", "title": "Python tutorial", "content": "Learn Python basics"})

    def test_all_rankings_return_results(self):
        for ranking in ["tf", "tfidf", "bm25"]:
            results = self.index.search("python", ranking=ranking)
            assert len(results["results"]) == 2

    def test_ranking_scores_positive(self):
        for ranking in ["tf", "tfidf", "bm25"]:
            results = self.index.search("python", ranking=ranking)
            for r in results["results"]:
                assert r["score"] > 0

    def test_default_ranking_is_tf(self):
        results_default = self.index.search("python")
        results_tf = self.index.search("python", ranking="tf")
        assert results_default["results"] == results_tf["results"]


class TestSnippetExtractor:
    """Tests for snippet extraction and highlighting."""

    def setup_method(self):
        self.extractor = SnippetExtractor(max_snippet_length=100)

    def test_extract_single_match(self):
        text = "This is a test document about python programming"
        snippets = self.extractor.extract(text, ["python"])
        assert len(snippets) == 1
        assert "python" in snippets[0].text.lower()
        assert "<mark>" in snippets[0].highlighted

    def test_extract_multiple_matches(self):
        text = "Python is great. Python is fun. Python is powerful."
        snippets = self.extractor.extract(text, ["python"])
        assert len(snippets) > 0
        assert "<mark>" in snippets[0].highlighted

    def test_extract_no_match(self):
        text = "This is a test document"
        snippets = self.extractor.extract(text, ["xyz"])
        assert len(snippets) == 1  # Fallback snippet
        assert "<mark>" not in snippets[0].highlighted

    def test_extract_empty_text(self):
        snippets = self.extractor.extract("", ["python"])
        assert snippets == []

    def test_extract_empty_terms(self):
        snippets = self.extractor.extract("some text", [])
        assert snippets == []

    def test_extract_with_ellipsis(self):
        text = "A" * 300 + " python " + "B" * 300
        snippets = self.extractor.extract(text, ["python"])
        assert len(snippets) == 1
        assert "..." in snippets[0].highlighted

    def test_extract_max_snippets(self):
        extractor = SnippetExtractor(max_snippets=2)
        text = "python here. " * 100
        snippets = extractor.extract(text, ["python"])
        assert len(snippets) <= 2

    def test_highlight_terms(self):
        text = "Hello python world"
        highlighted = self.extractor.highlight_text(text, ["python"])
        assert "<mark>python</mark>" in highlighted

    def test_highlight_case_insensitive(self):
        text = "Hello PYTHON world"
        highlighted = self.extractor.highlight_text(text, ["python"])
        assert "<mark>PYTHON</mark>" in highlighted

    def test_snippet_to_dict(self):
        snippet = Snippet(text="hello", highlighted="<mark>hello</mark>", matched_terms=["hello"])
        d = snippet.to_dict()
        assert d["text"] == "hello"
        assert d["highlighted"] == "<mark>hello</mark>"
        assert d["matched_terms"] == ["hello"]

    def test_custom_markers(self):
        extractor = SnippetExtractor(marker_open="**", marker_close="**")
        text = "Hello python world"
        highlighted = extractor.highlight_text(text, ["python"])
        assert "**python**" in highlighted


class TestSearchWithHighlight:
    """Tests for search with highlighting enabled."""

    def setup_method(self):
        self.search = ContentSearch()

    def test_search_with_highlight(self):
        self.search.index_items([
            {"id": "1", "title": "Python tutorial", "content": "Learn Python programming basics"},
        ])
        results = self.search.search("python", highlight=True)
        assert len(results["results"]) == 1
        assert "snippets" in results["results"][0]
        assert len(results["results"][0]["snippets"]) > 0

    def test_search_without_highlight(self):
        self.search.index_items([
            {"id": "1", "title": "Python tutorial", "content": "Learn Python programming basics"},
        ])
        results = self.search.search("python", highlight=False)
        assert len(results["results"]) == 1
        assert "snippets" not in results["results"][0]

    def test_search_highlight_with_tfidf(self):
        self.search.index_items([
            {"id": "1", "title": "Python tutorial", "content": "Learn Python programming basics"},
            {"id": "2", "title": "Java tutorial", "content": "Learn Java programming basics"},
        ])
        results = self.search.search("python", ranking="tfidf", highlight=True)
        assert len(results["results"]) == 1
        assert "snippets" in results["results"][0]

    def test_search_highlight_with_bm25(self):
        self.search.index_items([
            {"id": "1", "title": "Python tutorial", "content": "Learn Python programming basics"},
        ])
        results = self.search.search("python", ranking="bm25", highlight=True)
        assert len(results["results"]) == 1
        assert "snippets" in results["results"][0]
