"""Cycle 168 PROBE: personal_index/url_classifier.py (never-probed subsystem).

Adversarial deep tests for the URLClassifier:
  - classify: every category, confidence per rule, first-match-wins order,
    case-insensitivity, url preservation, reasons single-element, idempotence.
  - classify_batch / get_category_counts: empty, duplicates, unicode.
  - guard inputs: empty / whitespace / unicode / out-of-range (None documented).
  - one end-to-end run through the installed CLI (status).

The documented contract (classify docstring) was attacked and HOLDS:
  - confidence values per rule (redirect 0.8, feed 0.9, api 0.85, static 0.9,
    media 0.85, document 0.85, page 0.5) all match.
  - first-match-wins order (redirect > feed > api > static > media > document)
    holds for a URL matching several rules.
  - reasons is always a single-element list.
  - classify is idempotent and preserves the input url verbatim.
  - UNKNOWN is never returned (the default is PAGE).

NOTE on None: classify(None) raises AttributeError. This is OUT OF CONTRACT,
not a defect: the signature is `classify(self, url: str)` and the docstring
promises nothing about None input ("always returning a ClassificationResult"
and "Never returns None" refer to the RETURN value, not the input). The
sibling url_utils.is_valid_url guards None, but its contract explicitly
returns a bool for any input; url_classifier's contract is string-typed.
Pinned here as a documented crash (not xfail) so a future None-safety
contract change is caught.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.url_classifier import URLCategory, URLClassifier


@pytest.fixture
def clf() -> URLClassifier:
    return URLClassifier()


# ── clean armor: every category + confidence per rule ──────────────────


class TestCategoryConfidence:
    def test_redirect(self, clf):
        r = clf.classify("http://x.com/redirect")
        assert r.category is URLCategory.REDIRECT
        assert r.confidence == 0.8
        assert r.reasons == ["matches redirect pattern"]

    def test_feed(self, clf):
        r = clf.classify("http://x.com/feed")
        assert r.category is URLCategory.FEED
        assert r.confidence == 0.9
        assert r.reasons == ["matches feed pattern"]

    def test_api(self, clf):
        r = clf.classify("http://x.com/api/")
        assert r.category is URLCategory.API
        assert r.confidence == 0.85
        assert r.reasons == ["matches API pattern"]

    def test_static(self, clf):
        r = clf.classify("http://x.com/static/")
        assert r.category is URLCategory.STATIC
        assert r.confidence == 0.9
        assert r.reasons == ["matches static asset pattern"]

    def test_media(self, clf):
        r = clf.classify("http://x.com/a.png")
        assert r.category is URLCategory.MEDIA
        assert r.confidence == 0.85
        assert r.reasons == ["matches media pattern"]

    def test_document(self, clf):
        r = clf.classify("http://x.com/a.pdf")
        assert r.category is URLCategory.DOCUMENT
        assert r.confidence == 0.85
        assert r.reasons == ["matches document pattern"]

    def test_page_default(self, clf):
        r = clf.classify("http://x.com/plain")
        assert r.category is URLCategory.PAGE
        assert r.confidence == 0.5
        assert r.reasons == ["no specific pattern matched"]


# ── first-match-wins order ──────────────────────────────────────────────


class TestFirstMatchWins:
    def test_redirect_beats_feed_and_api(self, clf):
        # matches redirect + feed + api -> redirect wins (first in order).
        r = clf.classify("http://x.com/redirect/feed.json")
        assert r.category is URLCategory.REDIRECT

    def test_feed_beats_api(self, clf):
        r = clf.classify("http://x.com/feed.json")
        assert r.category is URLCategory.FEED

    def test_api_beats_static(self, clf):
        r = clf.classify("http://x.com/api/static/")
        assert r.category is URLCategory.API

    def test_static_beats_media(self, clf):
        r = clf.classify("http://x.com/static/a.png")
        assert r.category is URLCategory.STATIC


# ── case-insensitivity + url preservation ───────────────────────────────


class TestCaseAndPreservation:
    def test_uppercase_extension_matches_media(self, clf):
        r = clf.classify("http://x.com/PHOTO.JPG")
        assert r.category is URLCategory.MEDIA

    def test_url_preserved_verbatim(self, clf):
        r = clf.classify("HTTP://X.COM/Photo.JPG")
        assert r.url == "HTTP://X.COM/Photo.JPG"

    def test_mixed_case_path_matches(self, clf):
        r = clf.classify("http://x.com/API/V1")
        assert r.category is URLCategory.API


# ── guard inputs (in-contract) ──────────────────────────────────────────


class TestGuardInputs:
    def test_empty_string_is_page(self, clf):
        r = clf.classify("")
        assert r.category is URLCategory.PAGE
        assert r.url == ""

    def test_whitespace_string_is_page(self, clf):
        r = clf.classify("   ")
        assert r.category is URLCategory.PAGE

    def test_unicode_url_is_page(self, clf):
        r = clf.classify("http://пример.рф/путь")
        assert r.category is URLCategory.PAGE
        assert r.url == "http://пример.рф/путь"

    def test_relative_path_api(self, clf):
        r = clf.classify("/api/v1/users")
        assert r.category is URLCategory.API

    def test_fragment_does_not_match(self, clf):
        r = clf.classify("http://x.com/page#section")
        assert r.category is URLCategory.PAGE


# ── idempotence + property checks ───────────────────────────────────────


class TestIdempotenceAndProperties:
    def test_idempotent(self, clf):
        assert clf.classify("http://x.com/api/v1") == clf.classify(
            "http://x.com/api/v1"
        )

    def test_reasons_always_single_element(self, clf):
        for u in [
            "http://x.com/redirect",
            "http://x.com/plain",
            "http://x.com/a.png",
            "http://x.com/api/",
        ]:
            assert len(clf.classify(u).reasons) == 1

    def test_unknown_never_returned(self, clf):
        urls = [
            "http://x.com/",
            "http://x.com/a.png",
            "http://x.com/api/",
            "http://x.com/redirect",
            "http://x.com/feed",
            "http://x.com/a.pdf",
            "http://x.com/static/",
        ]
        for u in urls:
            assert clf.classify(u).category is not URLCategory.UNKNOWN

    def test_confidence_in_unit_interval(self, clf):
        for u in ["http://x.com/", "http://x.com/a.png", "http://x.com/api/"]:
            assert 0.0 <= clf.classify(u).confidence <= 1.0


# ── batch + counts ──────────────────────────────────────────────────────


class TestBatchAndCounts:
    def test_batch_empty(self, clf):
        assert clf.classify_batch([]) == []

    def test_counts_empty(self, clf):
        assert clf.get_category_counts([]) == {}

    def test_batch_matches_individual(self, clf):
        urls = ["http://x.com/api/", "http://x.com/a.png", "http://x.com/"]
        batch = clf.classify_batch(urls)
        assert [r.category for r in batch] == [
            clf.classify(u).category for u in urls
        ]

    def test_counts_duplicates(self, clf):
        urls = ["http://x.com/api/", "http://x.com/api/", "http://x.com/a.png"]
        counts = clf.get_category_counts(urls)
        assert counts["api"] == 2
        assert counts["media"] == 1

    def test_counts_unicode(self, clf):
        counts = clf.get_category_counts(["http://пример.рф/путь"])
        assert counts["page"] == 1


# ── documented out-of-contract crash (None) ─────────────────────────────


class TestNoneDocumented:
    """classify(None) raises AttributeError. This is OUT OF CONTRACT (the
    signature is `url: str` and the docstring promises nothing about None
    input), so it is NOT a defect and NOT xfail-pinned. It is documented
    here so a future None-safety contract change is caught by a red test."""

    def test_classify_none_raises(self, clf):
        with pytest.raises(AttributeError):
            clf.classify(None)

    def test_batch_none_raises(self, clf):
        with pytest.raises(TypeError):
            clf.classify_batch(None)

    def test_counts_none_raises(self, clf):
        with pytest.raises(TypeError):
            clf.get_category_counts(None)


# ── end-to-end through the installed CLI (status) ───────────────────────


class TestCliEndToEnd:
    def test_cli_status_runs(self, tmp_path):
        data_dir = str(tmp_path / "dd")
        run = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "status"],
            capture_output=True, text=True,
        )
        assert run.returncode == 0, run.stderr
        assert "Pages" in run.stdout or "pages" in run.stdout.lower()
