"""Adversarial deep tests for personal_index.content_enricher (never-probed subsystem).

Contract source: docs/content-enricher.md (Exact Contract) + the module docstrings.
"""

from __future__ import annotations

import subprocess
import sys

from personal_index.content_enricher import ContentEnricher


class TestEnrichGuardInputs:
    def test_empty_text_zero_metrics(self):
        e = ContentEnricher().enrich("t", "")
        assert e.word_count == 0
        assert e.reading_time == 0
        assert e.keywords == []
        assert e.sentiment_score == 0.0
        assert e.complexity_score == 0.0

    def test_whitespace_only_text(self):
        e = ContentEnricher().enrich("t", "   ")
        assert e.word_count == 0
        assert e.keywords == []
        assert e.sentiment_score == 0.0
        assert e.complexity_score == 0.0

    def test_none_title_passes_through(self):
        e = ContentEnricher().enrich(None, "hello world")
        assert e.title is None
        assert e.text == "hello world"
        assert e.word_count == 2

    def test_none_html_leaves_flags_false(self):
        e = ContentEnricher().enrich("t", "text", html=None)
        assert e.has_code is False
        assert e.has_links is False
        assert e.has_images is False

    def test_empty_html_leaves_flags_false(self):
        e = ContentEnricher().enrich("t", "text", html="")
        assert e.has_code is False
        assert e.has_links is False
        assert e.has_images is False


class TestEnrichHtmlDetection:
    def test_code_block_detected(self):
        e = ContentEnricher().enrich("t", "x", html="<pre>def f(): pass</pre>")
        assert e.has_code is True

    def test_inline_code_detected(self):
        e = ContentEnricher().enrich("t", "x", html="<code>x=1</code>")
        assert e.has_code is True

    def test_script_detected(self):
        e = ContentEnricher().enrich("t", "x", html="<script>var a=1;</script>")
        assert e.has_code is True

    def test_no_code_block(self):
        e = ContentEnricher().enrich("t", "x", html="<p>just text</p>")
        assert e.has_code is False

    def test_link_detected(self):
        e = ContentEnricher().enrich("t", "x", html='<a href="http://x">l</a>')
        assert e.has_links is True

    def test_link_without_href_not_detected(self):
        e = ContentEnricher().enrich("t", "x", html="<a>no href</a>")
        assert e.has_links is False

    def test_image_detected(self):
        e = ContentEnricher().enrich("t", "x", html='<img src="a.png">')
        assert e.has_images is True

    def test_image_without_src_not_detected(self):
        e = ContentEnricher().enrich("t", "x", html="<img alt=x>")
        assert e.has_images is False

    def test_case_insensitive_detection(self):
        e = ContentEnricher().enrich("t", "x", html="<PRE>code</PRE>")
        assert e.has_code is True


class TestSentimentScore:
    def test_neutral_text_zero(self):
        e = ContentEnricher().enrich("t", "the cat sat on the mat")
        assert e.sentiment_score == 0.0

    def test_all_positive_one(self):
        e = ContentEnricher().enrich("t", "good great excellent")
        assert e.sentiment_score == 1.0

    def test_all_negative_minus_one(self):
        e = ContentEnricher().enrich("t", "bad terrible awful")
        assert e.sentiment_score == -1.0

    def test_mixed_balanced_zero(self):
        e = ContentEnricher().enrich("t", "good bad")
        assert e.sentiment_score == 0.0

    def test_frequency_ignored_set_semantics(self):
        e = ContentEnricher().enrich("t", "good " * 10)
        assert e.sentiment_score == 1.0

    def test_score_always_in_range(self):
        for text in ["good good bad", "bad bad good", "excellent horrible", ""]:
            e = ContentEnricher().enrich("t", text)
            assert -1.0 <= e.sentiment_score <= 1.0


class TestComplexityScore:
    def test_empty_zero(self):
        assert ContentEnricher().enrich("t", "").complexity_score == 0.0

    def test_always_in_range(self):
        for text in ["a", "hello world", "x" * 100, "the quick brown fox"]:
            e = ContentEnricher().enrich("t", text)
            assert 0.0 <= e.complexity_score <= 1.0


class TestLanguageNeverComputed:
    def test_language_stays_en(self):
        e = ContentEnricher().enrich("t", "bonjour le monde", html="<p>x</p>")
        assert e.language == "en"

    def test_language_stays_en_empty(self):
        assert ContentEnricher().enrich("t", "").language == "en"


class TestKeywords:
    def test_top_n_zero_empty(self):
        e = ContentEnricher(top_n_keywords=0).enrich("t", "hello hello world")
        assert e.keywords == []

    def test_top_n_negative_empty(self):
        e = ContentEnricher(top_n_keywords=-5).enrich("t", "hello hello world")
        assert e.keywords == []

    def test_top_n_limits_count(self):
        e = ContentEnricher(top_n_keywords=2).enrich("t", "alpha alpha beta beta gamma gamma")
        assert len(e.keywords) <= 2

    def test_keywords_are_strings(self):
        e = ContentEnricher().enrich("t", "python python java")
        assert all(isinstance(k, str) for k in e.keywords)


class TestIdempotence:
    def test_enrich_deterministic_fields(self):
        e1 = ContentEnricher().enrich("t", "the quick brown fox jumps")
        e2 = ContentEnricher().enrich("t", "the quick brown fox jumps")
        for f in ("word_count", "reading_time", "keywords",
                  "sentiment_score", "complexity_score", "language"):
            assert getattr(e1, f) == getattr(e2, f)


class TestToDict:
    def test_key_set_exact(self):
        e = ContentEnricher().enrich("t", "hello world")
        d = e.to_dict()
        assert set(d.keys()) == {
            "title", "text", "word_count", "reading_time", "keywords",
            "language", "has_code", "has_links", "has_images",
            "sentiment_score", "complexity_score", "enriched_at",
        }

    def test_enriched_at_is_iso_string(self):
        d = ContentEnricher().enrich("t", "x").to_dict()
        assert isinstance(d["enriched_at"], str)
        from datetime import datetime
        datetime.fromisoformat(d["enriched_at"])

    def test_fields_match_dataclass(self):
        e = ContentEnricher().enrich("t", "hello world")
        d = e.to_dict()
        assert d["title"] == e.title
        assert d["text"] == e.text
        assert d["word_count"] == e.word_count
        assert d["keywords"] == e.keywords


class TestBatchEnrich:
    def test_empty_list(self):
        assert ContentEnricher().batch_enrich([]) == []

    def test_two_tuple_flags_false(self):
        out = ContentEnricher().batch_enrich([("t", "x")])
        assert len(out) == 1
        assert out[0].has_code is False
        assert out[0].has_links is False
        assert out[0].has_images is False

    def test_three_tuple_html_passthrough(self):
        out = ContentEnricher().batch_enrich([("t", "x", '<a href="http://x">l</a>')])
        assert out[0].has_links is True

    def test_batch_matches_single_enrich(self):
        html = '<pre>code</pre><img src="a.png">'
        single = ContentEnricher().enrich("t", "body", html=html)
        batch = ContentEnricher().batch_enrich([("t", "body", html)])[0]
        assert batch.has_code == single.has_code
        assert batch.has_images == single.has_images
        assert batch.has_links == single.has_links
        assert batch.word_count == single.word_count
        assert batch.keywords == single.keywords

    def test_mixed_arity_batch(self):
        out = ContentEnricher().batch_enrich([("a", "x"), ("b", "y", "<code>c</code>")])
        assert out[0].has_code is False
        assert out[1].has_code is True


class TestCliEndToEnd:
    def test_cli_help_runs(self):
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0
        assert "personal-index" in r.stdout.lower() or "usage" in r.stdout.lower()
