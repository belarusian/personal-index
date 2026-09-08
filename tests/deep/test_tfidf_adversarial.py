"""Adversarial deep tests for personal_index.tfidf.TfidfScorer.

PROBE target (cycle 152): the TF-IDF scorer is a never-probed subsystem with a
documented "top N" / "limit" contract. These tests attack that contract with
guard inputs (None/empty/whitespace/unicode/duplicate/out-of-range), round-trips,
idempotence, property checks, and one end-to-end run through the installed CLI
(`personal-index search --limit`).

Defect class surfaced (filed as QA-2): Python negative-slice semantics leak into
the "top N" / "limit" contract. `rank_documents(query, limit=-1)` and
`get_top_terms(doc_id, n=-1)` return `list[:-1]` (all-but-last) instead of an
empty list; the CLI `search --limit -1` (index.py SearchIndex.search) does the
same. Out-of-range (negative) N must yield an empty list, matching the n=0
guard.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from personal_index.cli import get_search_index, main
from personal_index.models import CrawledPage
from personal_index.tfidf import TfidfScorer


@pytest.fixture
def scorer() -> TfidfScorer:
    s = TfidfScorer()
    s.add_document("alpha beta gamma")
    s.add_document("beta delta epsilon")
    s.add_document("gamma zeta eta")
    return s


# ── main path (documented contract) ────────────────────────────────────
class TestMainPath:
    def test_add_document_returns_sequential_ids(self, scorer: TfidfScorer):
        assert scorer.document_count == 3
        assert scorer.vocabulary_size > 0

    def test_compute_tfidf_positive_scores(self, scorer: TfidfScorer):
        scores = scorer.compute_tfidf(0)
        assert set(scores) == {"alpha", "beta", "gamma"}
        assert all(v > 0 for v in scores.values())

    def test_rank_documents_positive_limit(self, scorer: TfidfScorer):
        ranked = scorer.rank_documents("beta", 10)
        # docs 0 and 1 both contain "beta"; doc 2 does not
        assert {doc_id for doc_id, _ in ranked} == {0, 1}
        assert all(score > 0 for _, score in ranked)

    def test_rank_documents_limit_zero_is_empty(self, scorer: TfidfScorer):
        assert scorer.rank_documents("beta", 0) == []

    def test_get_top_terms_positive_n(self, scorer: TfidfScorer):
        terms = scorer.get_top_terms(0, 10)
        assert [t for t, _ in terms] == ["alpha", "beta", "gamma"]
        assert all(score > 0 for _, score in terms)

    def test_get_top_terms_n_zero_is_empty(self, scorer: TfidfScorer):
        assert scorer.get_top_terms(0, 0) == []

    def test_score_query_known_term(self, scorer: TfidfScorer):
        assert scorer.score_query("beta", 0) > 0.0
        # doc 2 has no "beta"
        assert scorer.score_query("beta", 2) == 0.0


# ── guard inputs ───────────────────────────────────────────────────────
class TestGuardInputs:
    def test_empty_corpus_rank(self):
        s = TfidfScorer()
        assert s.rank_documents("beta") == []

    def test_empty_corpus_top_terms(self):
        s = TfidfScorer()
        assert s.get_top_terms(0) == []

    def test_empty_corpus_score_query(self):
        s = TfidfScorer()
        assert s.score_query("beta", 0) == 0.0

    def test_empty_corpus_compute_tfidf(self):
        s = TfidfScorer()
        assert s.compute_tfidf(0) == {}

    def test_empty_corpus_counts(self):
        s = TfidfScorer()
        assert s.document_count == 0
        assert s.vocabulary_size == 0

    def test_whitespace_only_document(self):
        s = TfidfScorer()
        doc_id = s.add_document("   \t\n  ")
        # tokenize yields no tokens -> no vocabulary, empty tfidf
        assert s.vocabulary_size == 0
        assert s.compute_tfidf(doc_id) == {}
        assert s.score_query("beta", doc_id) == 0.0

    def test_stopword_only_query_scores_zero(self, scorer: TfidfScorer):
        # "the and of" are all stopwords -> no query tokens -> 0.0
        assert scorer.score_query("the and of", 0) == 0.0

    def test_unknown_doc_id_score_zero(self, scorer: TfidfScorer):
        assert scorer.score_query("beta", 999) == 0.0

    def test_unknown_doc_id_compute_tfidf(self, scorer: TfidfScorer):
        assert scorer.compute_tfidf(999) == {}

    def test_unicode_document_yields_no_tokens(self):
        # tokenize is ASCII-only (documented regex); unicode silently drops.
        s = TfidfScorer()
        doc_id = s.add_document("café résumé naïve")
        assert s.compute_tfidf(doc_id) == {}
        assert s.score_query("café", doc_id) == 0.0


# ── remove / idempotence / round-trip ──────────────────────────────────
class TestRemoveAndIdempotence:
    def test_remove_document_round_trip(self):
        s = TfidfScorer()
        a = s.add_document("alpha beta")
        b = s.add_document("beta gamma")
        assert s.document_count == 2
        assert s.remove_document(a) is True
        assert s.document_count == 1
        # "alpha" was only in doc a -> gone from vocabulary
        assert "alpha" not in s.compute_tfidf(b) or s.compute_tfidf(b).get("alpha", 0) == 0
        assert s.vocabulary_size == len({"beta", "gamma"})

    def test_remove_document_idempotent(self):
        s = TfidfScorer()
        a = s.add_document("alpha beta")
        assert s.remove_document(a) is True
        # second remove of the same id is a no-op
        assert s.remove_document(a) is False
        assert s.document_count == 0

    def test_remove_bogus_id(self):
        s = TfidfScorer()
        s.add_document("alpha beta")
        assert s.remove_document(999) is False
        assert s.document_count == 1

    def test_remove_all_then_readd(self):
        s = TfidfScorer()
        a = s.add_document("alpha beta")
        s.remove_document(a)
        # re-adding after full removal works and resets doc freq cleanly
        b = s.add_document("alpha beta")
        assert s.document_count == 1
        assert set(s.compute_tfidf(b)) == {"alpha", "beta"}

    def test_clear_resets_state(self, scorer: TfidfScorer):
        scorer.clear()
        assert scorer.document_count == 0
        assert scorer.vocabulary_size == 0
        # ids restart at 0
        assert scorer.add_document("alpha beta") == 0


# ── property checks ────────────────────────────────────────────────────
class TestProperties:
    def test_tfidf_scores_bounded_and_positive(self, scorer: TfidfScorer):
        for doc_id in range(3):
            for term, score in scorer.compute_tfidf(doc_id).items():
                assert score > 0
                assert term in scorer._doc_terms[doc_id]

    def test_rank_documents_sorted_descending(self, scorer: TfidfScorer):
        ranked = scorer.rank_documents("beta", 10)
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_documents_respects_positive_limit(self, scorer: TfidfScorer):
        assert len(scorer.rank_documents("beta", 1)) <= 1
        assert len(scorer.rank_documents("beta", 2)) <= 2

    def test_get_top_terms_sorted_descending(self, scorer: TfidfScorer):
        terms = scorer.get_top_terms(0, 10)
        scores = [score for _, score in terms]
        assert scores == sorted(scores, reverse=True)

    def test_duplicate_documents_are_distinct_ids(self):
        s = TfidfScorer()
        a = s.add_document("alpha beta")
        b = s.add_document("alpha beta")
        assert a != b
        assert s.document_count == 2


# ── DEFECT: negative-slice leak (filed as QA-2) ────────────────────────
class TestNegativeSliceLeak:
    def test_rank_documents_negative_limit(self, scorer: TfidfScorer):
        assert scorer.rank_documents("beta", -1) == []

    def test_get_top_terms_negative_n(self, scorer: TfidfScorer):
        assert scorer.get_top_terms(0, -1) == []


# ── end-to-end CLI run (installed CLI) ─────────────────────────────────
class TestCliSearchEndToEnd:
    def _seed(self, dd: str) -> None:
        idx = get_search_index(dd)
        idx.add_page(CrawledPage(url="http://a", title="alpha beta",
                                 content="alpha beta gamma"))
        idx.add_page(CrawledPage(url="http://b", title="beta delta",
                                 content="beta delta epsilon"))

    def test_cli_search_valid_limit(self, tmp_path):
        dd = str(tmp_path / "data")
        self._seed(dd)
        result = CliRunner().invoke(
            main, ["search", "beta", "--limit", "10", "--data-dir", dd]
        )
        assert result.exit_code == 0, result.output
        assert "2 found" in result.output
        assert "http://a" in result.output
        assert "http://b" in result.output

    def test_cli_search_limit_zero(self, tmp_path):
        dd = str(tmp_path / "data")
        self._seed(dd)
        result = CliRunner().invoke(
            main, ["search", "beta", "--limit", "0", "--data-dir", dd]
        )
        assert result.exit_code == 0, result.output
        assert "No results found" in result.output

    def test_cli_search_negative_limit(self, tmp_path):
        dd = str(tmp_path / "data")
        self._seed(dd)
        result = CliRunner().invoke(
            main, ["search", "beta", "--limit", "-1", "--data-dir", dd]
        )
        assert result.exit_code == 0, result.output
        # negative limit must behave like limit=0 (no results)
        assert "No results found" in result.output
