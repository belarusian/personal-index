"""Tests for TF-IDF scoring module."""

from __future__ import annotations

from personal_index.tfidf import TfidfScorer


class TestTfidfScorer:
    """Tests for TfidfScorer class."""

    def setup_method(self):
        self.scorer = TfidfScorer()

    def test_add_document_returns_id(self):
        doc_id = self.scorer.add_document("hello world")
        assert doc_id == 0

    def test_add_multiple_documents(self):
        id1 = self.scorer.add_document("hello world")
        id2 = self.scorer.add_document("foo bar baz")
        assert id1 == 0
        assert id2 == 1
        assert self.scorer.document_count == 2

    def test_document_count(self):
        assert self.scorer.document_count == 0
        self.scorer.add_document("test")
        assert self.scorer.document_count == 1

    def test_vocabulary_size(self):
        self.scorer.add_document("hello world")
        self.scorer.add_document("hello foo")
        # "hello" and "world" and "foo" - 3 unique tokens
        assert self.scorer.vocabulary_size == 3

    def test_compute_tfidf_returns_dict(self):
        doc_id = self.scorer.add_document("hello world hello")
        scores = self.scorer.compute_tfidf(doc_id)
        assert isinstance(scores, dict)
        assert "hello" in scores
        assert "world" in scores

    def test_compute_tfidf_unknown_doc(self):
        scores = self.scorer.compute_tfidf(999)
        assert scores == {}

    def test_compute_tfidf_empty_corpus(self):
        scores = self.scorer.compute_tfidf(0)
        assert scores == {}

    def test_score_query_basic(self):
        doc_id = self.scorer.add_document("machine learning is great")
        score = self.scorer.score_query("machine learning", doc_id)
        assert score > 0

    def test_score_query_no_match(self):
        doc_id = self.scorer.add_document("hello world")
        score = self.scorer.score_query("foo bar", doc_id)
        assert score == 0.0

    def test_score_query_empty_query(self):
        self.scorer.add_document("hello world")
        score = self.scorer.score_query("", 0)
        assert score == 0.0

    def test_score_query_unknown_doc(self):
        self.scorer.add_document("hello world")
        score = self.scorer.score_query("hello", 999)
        assert score == 0.0

    def test_rank_documents(self):
        self.scorer.add_document("python programming language")
        self.scorer.add_document("javascript web development")
        self.scorer.add_document("python data science")
        results = self.scorer.rank_documents("python")
        assert len(results) >= 2
        # Docs with "python" should rank higher
        assert results[0][0] in (0, 2)

    def test_rank_documents_limit(self):
        for i in range(20):
            self.scorer.add_document(f"document number {i}")
        results = self.scorer.rank_documents("document", limit=5)
        assert len(results) <= 5

    def test_rank_documents_empty(self):
        results = self.scorer.rank_documents("test")
        assert results == []

    def test_remove_document(self):
        doc_id = self.scorer.add_document("hello world")
        assert self.scorer.remove_document(doc_id) is True
        assert self.scorer.document_count == 0

    def test_remove_unknown_document(self):
        assert self.scorer.remove_document(999) is False

    def test_get_top_terms(self):
        self.scorer.add_document("hello hello world")
        self.scorer.add_document("foo bar baz")
        top = self.scorer.get_top_terms(0, n=2)
        assert len(top) <= 2
        assert all(isinstance(t, tuple) and len(t) == 2 for t in top)

    def test_clear(self):
        self.scorer.add_document("hello world")
        self.scorer.clear()
        assert self.scorer.document_count == 0
        assert self.scorer.vocabulary_size == 0

    def test_tfidf_favors_rare_terms(self):
        """Rare terms should get higher IDF scores."""
        # "common" appears in all 3 docs, "rare" only in 1
        self.scorer.add_document("common word one")
        self.scorer.add_document("common word two")
        self.scorer.add_document("rare unique term")
        scores_common = self.scorer.compute_tfidf(0)
        scores_rare = self.scorer.compute_tfidf(2)
        # "common" appears in 3 docs, "rare" in 1 doc
        assert scores_rare.get("rare", 0) > scores_common.get("common", 0)

    def test_stopwords_filtered_in_tfidf(self):
        """Stop words should be filtered out during tokenization."""
        self.scorer.add_document("the quick brown fox")
        scores = self.scorer.compute_tfidf(0)
        assert "the" not in scores
        assert "quick" in scores

    def test_tfidf_higher_for_more_frequent_term(self):
        """Terms appearing more in a doc get higher TF component."""
        self.scorer.add_document("alpha alpha alpha beta")
        scores = self.scorer.compute_tfidf(0)
        assert scores["alpha"] > scores["beta"]

    def test_rank_documents_returns_sorted(self):
        """Results should be sorted by score descending."""
        self.scorer.add_document("alpha beta gamma")
        self.scorer.add_document("alpha alpha alpha")
        results = self.scorer.rank_documents("alpha")
        assert results[0][1] >= results[1][1]

    def test_score_query_case_insensitive(self):
        """Query matching should be case insensitive."""
        self.scorer.add_document("Hello World")
        score = self.scorer.score_query("HELLO", 0)
        assert score > 0

    def test_rank_documents_excludes_zero_score(self):
        """rank_documents only returns documents with positive TF-IDF score."""
        self.scorer.add_document("python programming language")
        self.scorer.add_document("completely unrelated text here")
        results = self.scorer.rank_documents("python")
        # Only the matching doc should appear; zero-score doc is excluded
        assert len(results) == 1
        assert results[0][0] == 0

    def test_score_query_is_query_tf_dot_doc_tfidf(self):
        """score_query = dot(query normalized-TF vector, doc TF-IDF vector).

        Pins the corrected docstring claim: the query side uses raw normalized
        term frequency (no IDF), only the document side is TF-IDF weighted.
        """
        from collections import Counter

        from personal_index.text_utils import tokenize

        doc_id = self.scorer.add_document("machine learning is great")
        query = "machine learning"
        # Guard path: all-stopword query yields no tokens -> 0.0
        assert self.scorer.score_query("the of and", doc_id) == 0.0
        # Guard path: unknown doc -> 0.0
        assert self.scorer.score_query(query, 999) == 0.0
        # Normal path: recompute the exact dot product the body performs.
        q_tokens = tokenize(query, remove_stopwords=True)
        q_counter = Counter(q_tokens)
        q_total = sum(q_counter.values())
        doc_tfidf = self.scorer.compute_tfidf(doc_id)
        expected = sum(
            (c / q_total) * doc_tfidf[t] for t, c in q_counter.items() if t in doc_tfidf
        )
        assert self.scorer.score_query(query, doc_id) == expected
        assert expected > 0
