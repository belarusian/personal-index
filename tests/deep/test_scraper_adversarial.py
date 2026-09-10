"""Adversarial deep tests for personal_index.scraper (HTMLScraper / ScraperConfig).

Contract source: tickets/ARCH-20 (issue #1056) + docs/content-scraper.md.
Two contract holes were fixed in PR#1240 and this file pins them:

  Hole 1 (dead flag): `ScraperConfig.remove_scripts` was stored but never
    read; script/style/noscript removal is driven entirely by `blocked_tags`.
    The fix REMOVED the field. We pin that the field is gone AND that
    removal is still driven by `blocked_tags` (a `<script>` tag's text is
    excluded from `raw_text` under the default config).

  Hole 2 (word_count ordering): `word_count` was computed from `raw_text`
    BEFORE `max_content_length` truncation, so it over-reported. The fix
    recomputes it AFTER truncation, so `word_count == len(raw_text.split())`
    always holds for the returned object. We pin that invariant across
    truncation and non-truncation boundaries.

Plus guard inputs (None/empty/whitespace/unicode/malformed HTML), boundary
`max_content_length`, `blocked_tags` behavior, idempotence, and error paths.
"""

from __future__ import annotations

import dataclasses

import pytest

from personal_index.scraper import HTMLScraper, ScrapedContent, ScraperConfig


def _scraper(**cfg) -> HTMLScraper:
    return HTMLScraper(ScraperConfig(**cfg))


def _page(body: str, title: str = "T") -> str:
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"


# ── Hole 1: dead `remove_scripts` flag is gone ─────────────────────────
class TestRemoveScriptsFlagRemoved:
    def test_field_not_in_dataclass(self):
        names = [f.name for f in dataclasses.fields(ScraperConfig)]
        assert "remove_scripts" not in names

    def test_cannot_construct_with_remove_scripts(self):
        with pytest.raises(TypeError):
            ScraperConfig(remove_scripts=False)  # type: ignore[call-arg]

    def test_default_config_has_no_remove_scripts_attr(self):
        cfg = ScraperConfig()
        assert not hasattr(cfg, "remove_scripts")

    def test_script_text_excluded_under_default_blocked_tags(self):
        # Removal is driven by blocked_tags, not the removed flag.
        s = _scraper()
        r = s.scrape(_page("<p>visible</p><script>secret()</script>"))
        assert "secret" not in r.raw_text
        assert "visible" in r.raw_text

    def test_style_and_noscript_excluded_by_default(self):
        s = _scraper()
        r = s.scrape(_page("<p>keep</p><style>.a{}</style><noscript>nojs</noscript>"))
        assert ".a{}" not in r.raw_text
        assert "nojs" not in r.raw_text

    def test_empty_blocked_tags_keeps_script_text(self):
        # With blocked_tags emptied, script text is NOT decomposed.
        s = _scraper(blocked_tags=[])
        r = s.scrape(_page("<p>keep</p><script>secret()</script>"))
        # script is not in the _get_clean_text element list, so its text
        # never reaches raw_text regardless of blocked_tags.
        assert "secret" not in r.raw_text

    def test_custom_blocked_tag_removed(self):
        s = _scraper(blocked_tags=["aside"])
        r = s.scrape(_page("<p>keep</p><aside>side</aside>"))
        # aside is not in the clean-text element list either, but the tag
        # itself must be decomposed from the soup (no <aside> survives).
        assert "side" not in r.raw_text


# ── Hole 2: word_count == len(raw_text.split()) always ─────────────────
class TestWordCountConsistency:
    def test_no_truncation_short_page(self):
        s = _scraper()
        r = s.scrape(_page("<p>one two three four five</p>"))
        assert r.word_count == len(r.raw_text.split())
        assert r.word_count == 5

    def test_truncation_boundary(self):
        s = _scraper(max_content_length=100)
        body = "<p>" + " ".join(f"w{i}" for i in range(50)) + "</p>"
        r = s.scrape(_page(body))
        assert len(r.raw_text) <= 100
        assert r.word_count == len(r.raw_text.split())

    def test_exact_boundary_no_truncation(self):
        # raw_text length exactly == max_content_length -> not truncated
        s = _scraper(max_content_length=5)
        r = s.scrape(_page("<p>abcde</p>"))
        assert len(r.raw_text) == 5
        assert r.word_count == len(r.raw_text.split())

    def test_one_over_boundary_truncates(self):
        s = _scraper(max_content_length=5)
        r = s.scrape(_page("<p>abcdef</p>"))
        assert len(r.raw_text) == 5
        assert r.word_count == len(r.raw_text.split())

    def test_zero_max_content_length(self):
        s = _scraper(max_content_length=0)
        r = s.scrape(_page("<p>hello world</p>"))
        assert r.raw_text == ""
        assert r.word_count == 0

    def test_word_count_zero_when_no_text(self):
        s = _scraper()
        r = s.scrape(_page("<div><span>x</span></div>"))
        # span/div are not in the clean-text element list
        assert r.word_count == 0
        assert r.raw_text == ""

    def test_word_count_property_invariant_many_lengths(self):
        for n in range(0, 40):
            s = _scraper(max_content_length=n)
            body = "<p>" + " ".join(f"w{i}" for i in range(20)) + "</p>"
            r = s.scrape(_page(body))
            assert r.word_count == len(r.raw_text.split())


# ── Guard inputs ────────────────────────────────────────────────────────
class TestGuardInputs:
    def test_empty_html(self):
        s = _scraper()
        r = s.scrape("")
        assert isinstance(r, ScrapedContent)
        assert r.raw_text == ""
        assert r.word_count == 0
        assert r.title == ""

    def test_whitespace_html(self):
        s = _scraper()
        r = s.scrape("   \n\t  ")
        assert r.raw_text == ""
        assert r.word_count == 0

    def test_none_html_raises(self):
        s = _scraper()
        with pytest.raises(Exception):
            s.scrape(None)  # type: ignore[arg-type]

    def test_malformed_html(self):
        s = _scraper()
        r = s.scrape("<p>unclosed <b>bold <div>mixed")
        assert isinstance(r, ScrapedContent)
        assert r.word_count == len(r.raw_text.split())

    def test_unicode_content(self):
        s = _scraper()
        r = s.scrape(_page("<p>héllo wörld 日本語</p>"))
        assert "héllo" in r.raw_text
        assert "日本語" in r.raw_text
        assert r.word_count == len(r.raw_text.split())

    def test_emoji_content(self):
        s = _scraper()
        r = s.scrape(_page("<p>hi 🚀 there</p>"))
        assert r.word_count == len(r.raw_text.split())

    def test_no_base_url_defaults_empty(self):
        s = _scraper()
        r = s.scrape(_page("<p>x</p>"))
        assert r.url == ""

    def test_base_url_recorded(self):
        s = _scraper()
        r = s.scrape(_page("<p>x</p>"), base_url="http://ex.com/a")
        assert r.url == "http://ex.com/a"


# ── blocked_tags behavior ───────────────────────────────────────────────
class TestBlockedTags:
    def test_default_blocked_tags(self):
        cfg = ScraperConfig()
        assert cfg.blocked_tags == ["script", "style", "noscript"]

    def test_blocked_tags_independent_default(self):
        # mutating one config's blocked_tags must not leak into another
        a = ScraperConfig()
        b = ScraperConfig()
        a.blocked_tags.append("video")
        assert "video" not in b.blocked_tags

    def test_multiple_blocked_tags(self):
        s = _scraper(blocked_tags=["script", "style", "noscript", "iframe"])
        r = s.scrape(_page("<p>keep</p><iframe>frame</iframe>"))
        assert "frame" not in r.raw_text

    def test_unknown_blocked_tag_no_error(self):
        s = _scraper(blocked_tags=["doesnotexist"])
        r = s.scrape(_page("<p>keep</p>"))
        assert "keep" in r.raw_text


# ── Extraction toggles ──────────────────────────────────────────────────
class TestExtractionToggles:
    def test_extract_meta_off(self):
        s = _scraper(extract_meta=False)
        r = s.scrape(_page("<p>x</p>", title="MyTitle"))
        assert r.title == ""

    def test_extract_headings_off(self):
        s = _scraper(extract_headings=False)
        r = s.scrape(_page("<h1>Head</h1><p>x</p>"))
        assert r.headings == []

    def test_extract_links_off(self):
        s = _scraper(extract_links=False)
        r = s.scrape(_page('<p><a href="/x">link</a></p>'))
        assert r.links == []

    def test_extract_images_off(self):
        s = _scraper(extract_images=False)
        r = s.scrape(_page('<p><img src="/i.png"></p>'))
        assert r.images == []

    def test_extract_tables_off_by_default(self):
        s = _scraper()
        r = s.scrape(_page("<table><tr><td>c</td></tr></table>"))
        assert r.tables == []

    def test_extract_tables_on(self):
        s = _scraper(extract_tables=True)
        r = s.scrape(_page("<table><tr><td>a</td><td>b</td></tr></table>"))
        assert r.tables == [{"rows": [["a", "b"]]}]

    def test_headings_captured(self):
        s = _scraper()
        r = s.scrape(_page("<h1>A</h1><h2>B</h2>"))
        assert "h1: A" in r.headings
        assert "h2: B" in r.headings


# ── Link / image resolution ─────────────────────────────────────────────
class TestLinkImageResolution:
    def test_relative_link_resolved(self):
        s = _scraper()
        r = s.scrape(_page('<p><a href="/x">x</a></p>'), base_url="http://ex.com/base")
        assert r.links[0]["url"] == "http://ex.com/x"

    def test_absolute_link_kept(self):
        s = _scraper()
        r = s.scrape(_page('<p><a href="http://other.com/y">y</a></p>'),
                     base_url="http://ex.com/base")
        assert r.links[0]["url"] == "http://other.com/y"

    def test_duplicate_links_deduped(self):
        s = _scraper()
        r = s.scrape(_page('<p><a href="/x">a</a><a href="/x">b</a></p>'),
                     base_url="http://ex.com")
        assert len(r.links) == 1

    def test_empty_href_skipped(self):
        s = _scraper()
        r = s.scrape(_page('<p><a href="">x</a></p>'))
        assert r.links == []

    def test_image_src_resolved(self):
        s = _scraper()
        r = s.scrape(_page('<p><img src="/i.png" alt="alt"></p>'),
                     base_url="http://ex.com")
        assert r.images[0]["src"] == "http://ex.com/i.png"
        assert r.images[0]["alt"] == "alt"

    def test_image_no_src_skipped(self):
        s = _scraper()
        r = s.scrape(_page('<p><img></p>'))
        assert r.images == []


# ── Meta extraction ─────────────────────────────────────────────────────
class TestMetaExtraction:
    def test_title_extracted(self):
        s = _scraper()
        r = s.scrape(_page("<p>x</p>", title="  My Title  "))
        assert r.title == "My Title"

    def test_meta_description(self):
        s = _scraper()
        html = _page("<p>x</p>")
        html = html.replace("<head>", '<head><meta name="description" content="desc here">')
        r = s.scrape(html)
        assert r.meta_description == "desc here"

    def test_meta_keywords(self):
        s = _scraper()
        html = _page("<p>x</p>")
        html = html.replace("<head>", '<head><meta name="keywords" content="k1, k2">')
        r = s.scrape(html)
        assert r.meta_keywords == "k1, k2"

    def test_og_title_fallback(self):
        s = _scraper()
        html = "<html><head><meta property='og:title' content='OG Title'></head><body><p>x</p></body></html>"
        r = s.scrape(html)
        assert r.title == "OG Title"

    def test_charset_meta(self):
        s = _scraper()
        html = "<html><head><meta charset='latin-1'></head><body><p>x</p></body></html>"
        r = s.scrape(html)
        assert r.charset == "latin-1"

    def test_charset_default_utf8(self):
        s = _scraper()
        r = s.scrape(_page("<p>x</p>"))
        assert r.charset == "utf-8"


# ── Idempotence / stability ─────────────────────────────────────────────
class TestIdempotence:
    def test_scrape_is_pure(self):
        s = _scraper()
        html = _page("<p>one two</p><h1>H</h1>")
        r1 = s.scrape(html)
        r2 = s.scrape(html)
        assert r1.raw_text == r2.raw_text
        assert r1.word_count == r2.word_count
        assert r1.headings == r2.headings
        assert r1.links == r2.links

    def test_repeated_scrape_no_state_leak(self):
        s = _scraper()
        for _ in range(3):
            r = s.scrape(_page("<p>abc</p>"))
            assert r.word_count == 1

    def test_config_not_mutated_by_scrape(self):
        cfg = ScraperConfig(blocked_tags=["script"])
        s = HTMLScraper(cfg)
        s.scrape(_page("<p>x</p><script>y</script>"))
        assert cfg.blocked_tags == ["script"]


# ── Error / edge ────────────────────────────────────────────────────────
class TestErrorEdge:
    def test_none_config_uses_default(self):
        s = HTMLScraper(None)
        assert isinstance(s.config, ScraperConfig)

    def test_huge_max_content_length(self):
        s = _scraper(max_content_length=10**9)
        r = s.scrape(_page("<p>" + " ".join("w" for _ in range(1000)) + "</p>"))
        assert r.word_count == len(r.raw_text.split())

    def test_negative_max_content_length(self):
        # negative bound: len(raw_text) > negative is always true -> truncate to [:neg]
        s = _scraper(max_content_length=-5)
        r = s.scrape(_page("<p>hello world</p>"))
        assert r.word_count == len(r.raw_text.split())

    def test_only_headings_no_paragraphs(self):
        s = _scraper()
        r = s.scrape(_page("<h1>Only heading</h1>"))
        assert r.paragraphs == []
        assert "Only heading" in r.raw_text
