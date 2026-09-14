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

    def test_add_document_zero_term_does_not_inflate_idf(self):
        """A zero-term (empty) document is a no-op that does not shift scores.

        Pins the corrected behavior against the returned object: adding an
        empty document must not raise _doc_count, so the existing document's
        TF-IDF scores are unchanged (the IDF denominator is not inflated).
        """
        d0 = self.scorer.add_document("cat sat")
        assert self.scorer.compute_tfidf(d0) == {"cat": 0.5, "sat": 0.5}
        # Zero-term document: no-op, must not shift the existing scores.
        self.scorer.add_document("")
        assert self.scorer.compute_tfidf(d0) == {"cat": 0.5, "sat": 0.5}
        # The zero-term document is not counted toward the corpus.
        assert self.scorer.document_count == 1

    def test_add_document_all_stopwords_is_noop(self):
        """An all-stopword document is a no-op: corpus state is untouched."""
        d0 = self.scorer.add_document("cat sat")
        before_count = self.scorer.document_count
        before_vocab = self.scorer.vocabulary_size
        before_scores = self.scorer.compute_tfidf(d0)
        # All-stopword input tokenizes to zero terms -> no-op.
        self.scorer.add_document("the")
        assert self.scorer.document_count == before_count
        assert self.scorer.vocabulary_size == before_vocab
        assert self.scorer.compute_tfidf(d0) == before_scores

    def test_add_document_normal_docs_unchanged(self):
        """Two real documents behave exactly as before (2-doc IDF denominator)."""
        import math

        d0 = self.scorer.add_document("cat sat")
        d1 = self.scorer.add_document("dog runs")
        assert self.scorer.document_count == 2
        # 'cat' appears in only one of the two docs: df=1, doc_count=2,
        # so the IDF uses the two-document denominator.
        expected_idf = math.log((1 + 2) / (1 + 1)) + 1
        expected = 0.5 * expected_idf
        assert self.scorer.compute_tfidf(d0) == {"cat": expected, "sat": expected}
        assert self.scorer.compute_tfidf(d1) == {"dog": expected, "runs": expected}

    def test_remove_zero_term_document_is_noop(self):
        """Removing a zero-term document's id returns False and leaves corpus."""
        d0 = self.scorer.add_document("cat sat")
        before_scores = self.scorer.compute_tfidf(d0)
        # Zero-term document: id assigned but never stored in the corpus.
        empty_id = self.scorer.add_document("")
        assert self.scorer.remove_document(empty_id) is False
        # Corpus untouched: the real document is still scored identically.
        assert self.scorer.compute_tfidf(d0) == before_scores
        assert self.scorer.document_count == 1
