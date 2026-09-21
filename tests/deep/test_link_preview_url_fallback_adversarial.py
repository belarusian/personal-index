"""Deep adversarial pins for LinkPreviewGenerator.generate url-fallback (ARCH-78).

Contract (personal_index/link_preview.py, generate() docstring):
  - url: og:url first; when og:url is absent/empty, falls back to base_url
    (the URL the caller is previewing); when both are empty, url stays "".
  - image_url: og:image > twitter:image, resolved against base_url via urljoin
    (absolute image stays absolute; relative image is urljoined; no base -> verbatim).

This file pins the ARCH-78 url-fallback behavior that landed 2026-09-15
(a445976) AFTER the original test_link_preview_adversarial.py was written
(09-09), so the fallback path was previously un-pinned. All assertions are
re-derived against the ACTUAL result shape on current main (cycle 352).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.link_preview import LinkPreview, LinkPreviewGenerator


@pytest.fixture
def gen() -> LinkPreviewGenerator:
    return LinkPreviewGenerator()


# ---------------------------------------------------------------------------
# ARCH-78: url falls back to base_url when og:url is absent/empty
# ---------------------------------------------------------------------------


class TestUrlFallbackToBaseUrl:
    def test_og_url_absent_falls_back_to_base_url(self, gen):
        # og:url tag entirely absent -> url == base_url (the ARCH-78 change)
        p = gen.generate('<meta property="og:title" content="T">', "http://b.com/page")
        assert p.url == "http://b.com/page"

    def test_og_url_present_wins_over_base_url(self, gen):
        # og:url present -> url == og:url, base_url ignored for the url field
        p = gen.generate('<meta property="og:url" content="http://u.com">', "http://b.com")
        assert p.url == "http://u.com"

    def test_og_url_empty_content_falls_back_to_base_url(self, gen):
        # og:url present but content empty -> treated absent -> base_url
        p = gen.generate('<meta property="og:url" content="">', "http://b.com")
        assert p.url == "http://b.com"

    def test_og_url_whitespace_content_falls_back_to_base_url(self, gen):
        # og:url whitespace-only content -> stripped to empty -> base_url
        p = gen.generate('<meta property="og:url" content="   ">', "http://b.com")
        assert p.url == "http://b.com"

    def test_og_url_surrounding_whitespace_stripped(self, gen):
        # og:url with surrounding whitespace -> stripped, base_url ignored
        p = gen.generate('<meta property="og:url" content="  http://u.com  ">', "http://b.com")
        assert p.url == "http://u.com"

    def test_both_og_url_and_base_empty_stays_empty(self, gen):
        # no og:url AND no base_url -> url stays ""
        p = gen.generate('<meta property="og:title" content="T">', "")
        assert p.url == ""

    def test_og_url_absent_no_base_stays_empty(self, gen):
        # no og:url, base_url default "" -> url stays ""
        p = gen.generate('<meta property="og:title" content="T">')
        assert p.url == ""

    def test_unicode_base_url_fallback(self, gen):
        # unicode base_url is preserved verbatim in the fallback
        p = gen.generate('<meta property="og:title" content="T">', "http://例え.com/x")
        assert p.url == "http://例え.com/x"

    def test_relative_og_url_not_urljoined(self, gen):
        # url field is taken verbatim (NOT urljoined, unlike image_url);
        # a relative og:url stays relative per the contract
        p = gen.generate('<meta property="og:url" content="/rel/path">', "http://b.com")
        assert p.url == "/rel/path"


# ---------------------------------------------------------------------------
# image_url resolution invariants (urljoin against base_url)
# ---------------------------------------------------------------------------


class TestImageUrlResolution:
    def test_relative_image_urljoined_against_base(self, gen):
        p = gen.generate('<meta property="og:image" content="/i.png">', "http://b.com/dir/")
        assert p.image_url == "http://b.com/i.png"

    def test_absolute_image_url_preserved(self, gen):
        p = gen.generate('<meta property="og:image" content="http://img.com/i.png">', "http://b.com/")
        assert p.image_url == "http://img.com/i.png"

    def test_relative_image_no_base_verbatim(self, gen):
        # no base_url -> relative image stays verbatim (urljoin not applied)
        p = gen.generate('<meta property="og:image" content="/i.png">', "")
        assert p.image_url == "/i.png"

    def test_no_image_no_base_empty(self, gen):
        p = gen.generate('<meta property="og:title" content="T">', "")
        assert p.image_url == ""


# ---------------------------------------------------------------------------
# Idempotence / round-trip on the url-fallback path
# ---------------------------------------------------------------------------


class TestUrlFallbackIdempotence:
    def test_idempotent_fallback(self, gen):
        html = '<meta property="og:title" content="T">'
        assert gen.generate(html, "http://b.com") == gen.generate(html, "http://b.com")

    def test_fallback_equals_explicit_dataclass(self, gen):
        # fallback result equals a hand-built LinkPreview with url=base_url
        p = gen.generate('<meta property="og:title" content="T">', "http://b.com")
        assert p == LinkPreview(title="T", url="http://b.com")


# ---------------------------------------------------------------------------
# End-to-end CLI run (link_preview has no dedicated CLI command; exercise the
# installed CLI entry point to confirm the module imports cleanly in-process
# and the CLI still runs green after the ARCH-78 change).
# ---------------------------------------------------------------------------


class TestCliEndToEnd:
    def test_cli_help_runs_green(self):
        # The CLI entry point must run and exit 0; link_preview is imported by
        # the package, so a broken import would surface here.
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "Usage" in proc.stdout

    def test_cli_version_runs_green(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
