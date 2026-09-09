"""Adversarial deep tests for personal_index.link_preview.

Cycle 182 — VALIDATOR probe.

Covers: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, ordering/stability, boundary lengths,
defensive loads, error contracts, and one end-to-end run through the
installed CLI entry point.

The module's contract (from docstrings):
- LinkPreview: dataclass with 8 str fields, all defaulting to ""
- LinkPreviewGenerator.generate(html, base_url="") -> LinkPreview
  - empty/None html -> empty LinkPreview (all fields "")
  - title: og:title > twitter:title > <title> tag
  - description: og:description > twitter:description > meta[name=description]
  - image_url: og:image > twitter:image, resolved against base_url via urljoin
  - site_name/type/url/locale: og:* only
  - twitter_card: twitter:card
  - all extracted values are .strip()ped
  - empty/whitespace content attributes fall through the chain (falsy)
  - <title> is RCDATA: nested markup is literal text, not parsed
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
# Empty / None / guard inputs
# ---------------------------------------------------------------------------

class TestEmptyAndNoneInputs:
    def test_none_input_returns_empty_preview(self, gen):
        p = gen.generate(None)
        assert p == LinkPreview()
        assert p.title == "" and p.description == "" and p.image_url == ""

    def test_empty_string_returns_empty_preview(self, gen):
        p = gen.generate("")
        assert p == LinkPreview()

    def test_whitespace_only_returns_empty_preview(self, gen):
        p = gen.generate("   \n\t  ")
        assert p == LinkPreview()

    def test_bytes_input_accepted(self, gen):
        p = gen.generate(b"<html><head><title>Bytes</title></head></html>")
        assert p.title == "Bytes"

    @pytest.mark.parametrize("bad", [123, True, ["<title>X</title>"], 3.14])
    def test_non_string_input_raises(self, gen, bad):
        with pytest.raises(TypeError):
            gen.generate(bad)


# ---------------------------------------------------------------------------
# Unicode
# ---------------------------------------------------------------------------

class TestUnicode:
    def test_unicode_title(self, gen):
        html = '<meta property="og:title" content="Привет 世界 🌍">'
        assert gen.generate(html).title == "Привет 世界 🌍"

    def test_unicode_description(self, gen):
        html = '<meta property="og:description" content="café naïve 日本語">'
        assert gen.generate(html).description == "café naïve 日本語"

    def test_unicode_image_url(self, gen):
        html = '<meta property="og:image" content="/img/файл.png">'
        assert gen.generate(html, "http://s.com").image_url == "http://s.com/img/файл.png"

    def test_unicode_all_fields(self, gen):
        html = (
            '<meta property="og:title" content="Tïtle">'
            '<meta property="og:description" content="Dësc">'
            '<meta property="og:site_name" content="Sïte">'
            '<meta property="og:locale" content="de_DE">'
        )
        p = gen.generate(html)
        assert p.title == "Tïtle"
        assert p.description == "Dësc"
        assert p.site_name == "Sïte"
        assert p.locale == "de_DE"


# ---------------------------------------------------------------------------
# Priority and fallback chains
# ---------------------------------------------------------------------------

class TestPriorityAndFallback:
    def test_title_og_priority_over_twitter_and_title_tag(self, gen):
        html = (
            '<meta property="og:title" content="OGT">'
            '<meta name="twitter:title" content="TWT">'
            "<title>TT</title>"
        )
        assert gen.generate(html).title == "OGT"

    def test_title_twitter_priority_over_title_tag(self, gen):
        html = '<meta name="twitter:title" content="TWT"><title>TT</title>'
        assert gen.generate(html).title == "TWT"

    def test_title_fallback_to_title_tag(self, gen):
        assert gen.generate("<title>TT</title>").title == "TT"

    def test_description_og_priority(self, gen):
        html = (
            '<meta property="og:description" content="OGD">'
            '<meta name="twitter:description" content="TWD">'
            '<meta name="description" content="STD">'
        )
        assert gen.generate(html).description == "OGD"

    def test_description_twitter_priority(self, gen):
        html = (
            '<meta name="twitter:description" content="TWD">'
            '<meta name="description" content="STD">'
        )
        assert gen.generate(html).description == "TWD"

    def test_description_standard_meta_fallback(self, gen):
        assert gen.generate('<meta name="description" content="STD">').description == "STD"

    def test_description_no_source_empty(self, gen):
        assert gen.generate("<html></html>").description == ""

    def test_image_og_priority_over_twitter(self, gen):
        html = (
            '<meta property="og:image" content="/og.png">'
            '<meta name="twitter:image" content="/tw.png">'
        )
        assert gen.generate(html, "http://s.com").image_url == "http://s.com/og.png"

    def test_image_twitter_fallback(self, gen):
        html = '<meta name="twitter:image" content="/tw.png">'
        assert gen.generate(html, "http://s.com").image_url == "http://s.com/tw.png"

    def test_empty_og_content_falls_through_to_twitter(self, gen):
        html = '<meta property="og:title" content=""><meta name="twitter:title" content="TWT">'
        assert gen.generate(html).title == "TWT"

    def test_whitespace_og_content_falls_through(self, gen):
        html = '<meta property="og:title" content="   "><meta name="twitter:title" content="TWT">'
        assert gen.generate(html).title == "TWT"

    def test_missing_content_attr_falls_through(self, gen):
        html = '<meta property="og:title"><title>TT</title>'
        assert gen.generate(html).title == "TT"

    def test_wrong_attr_name_ignored(self, gen):
        # og:title must use property=, not name=
        html = '<meta name="og:title" content="WRONG"><title>TT</title>'
        assert gen.generate(html).title == "TT"


# ---------------------------------------------------------------------------
# Duplicate / ordering / stability
# ---------------------------------------------------------------------------

class TestDuplicateAndOrdering:
    def test_duplicate_og_title_first_wins(self, gen):
        html = (
            '<meta property="og:title" content="FIRST">'
            '<meta property="og:title" content="SECOND">'
        )
        assert gen.generate(html).title == "FIRST"

    def test_first_empty_second_content_falls_through(self, gen):
        # find() returns the FIRST matching tag; empty content is falsy -> title tag
        html = (
            '<meta property="og:title" content="">'
            '<meta property="og:title" content="SECOND">'
            "<title>TT</title>"
        )
        assert gen.generate(html).title == "TT"

    def test_stable_across_repeated_calls(self, gen):
        html = (
            '<meta property="og:title" content="T">'
            '<meta property="og:description" content="D">'
            "<title>TT</title>"
        )
        results = [gen.generate(html, "http://b.com") for _ in range(5)]
        assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# <title> tag (RCDATA semantics)
# ---------------------------------------------------------------------------

class TestTitleTag:
    def test_title_tag_text(self, gen):
        assert gen.generate("<title>Plain</title>").title == "Plain"

    def test_title_tag_whitespace_stripped(self, gen):
        assert gen.generate("<title>   Padded   </title>").title == "Padded"

    def test_title_tag_empty(self, gen):
        assert gen.generate("<title></title>").title == ""

    def test_title_tag_whitespace_only(self, gen):
        assert gen.generate("<title>   </title>").title == ""

    def test_title_tag_rcdata_literal(self, gen):
        # <title> is RCDATA: nested markup is literal text, not parsed.
        # This is correct HTML behavior, not a defect.
        assert gen.generate("<title><b>Hi</b></title>").title == "<b>Hi</b>"

    def test_title_tag_multiple_children_literal(self, gen):
        assert gen.generate("<title><b>Hi</b> <i>there</i></title>").title == "<b>Hi</b> <i>there</i>"


# ---------------------------------------------------------------------------
# Image URL resolution (urljoin)
# ---------------------------------------------------------------------------

class TestImageResolution:
    def test_absolute_image_with_base(self, gen):
        html = '<meta property="og:image" content="https://cdn.com/a.png">'
        assert gen.generate(html, "http://site.com/page").image_url == "https://cdn.com/a.png"

    def test_root_relative_image_with_base(self, gen):
        html = '<meta property="og:image" content="/img/a.png">'
        assert gen.generate(html, "http://site.com/page").image_url == "http://site.com/img/a.png"

    def test_relative_image_with_base(self, gen):
        html = '<meta property="og:image" content="a.png">'
        assert gen.generate(html, "http://site.com/dir/page").image_url == "http://site.com/dir/a.png"

    def test_protocol_relative_image(self, gen):
        html = '<meta property="og:image" content="//cdn.com/a.png">'
        assert gen.generate(html, "http://site.com/page").image_url == "http://cdn.com/a.png"

    def test_relative_image_no_base_returned_as_is(self, gen):
        html = '<meta property="og:image" content="/img/a.png">'
        assert gen.generate(html, "").image_url == "/img/a.png"

    def test_empty_image(self, gen):
        html = '<meta property="og:image" content="">'
        assert gen.generate(html, "http://site.com/page").image_url == ""

    def test_base_with_query_string(self, gen):
        html = '<meta property="og:image" content="a.png">'
        assert gen.generate(html, "http://s.com/p?x=1").image_url == "http://s.com/a.png"

    def test_base_trailing_slash(self, gen):
        html = '<meta property="og:image" content="a.png">'
        assert gen.generate(html, "http://s.com/dir/").image_url == "http://s.com/dir/a.png"


# ---------------------------------------------------------------------------
# Idempotence / round-trip / dataclass
# ---------------------------------------------------------------------------

class TestIdempotenceAndRoundTrip:
    def test_idempotent_same_input(self, gen):
        html = '<meta property="og:title" content="T"><title>TT</title>'
        assert gen.generate(html, "http://b.com") == gen.generate(html, "http://b.com")

    def test_dataclass_default_all_empty(self):
        d = LinkPreview()
        assert d.title == "" and d.description == ""
        assert d.image_url == "" and d.site_name == ""
        assert d.type == "" and d.url == ""
        assert d.twitter_card == "" and d.locale == ""

    def test_dataclass_equality(self, gen):
        html = '<meta property="og:title" content="T">'
        assert gen.generate(html) == LinkPreview(title="T")

    def test_round_trip_all_fields(self, gen):
        html = (
            '<meta property="og:title" content="T">'
            '<meta property="og:description" content="D">'
            '<meta property="og:image" content="/i.png">'
            '<meta property="og:site_name" content="S">'
            '<meta property="og:type" content="article">'
            '<meta property="og:url" content="http://u.com">'
            '<meta property="og:locale" content="en_US">'
            '<meta name="twitter:card" content="summary_large_image">'
        )
        p = gen.generate(html, "http://b.com")
        assert p.title == "T"
        assert p.description == "D"
        assert p.image_url == "http://b.com/i.png"
        assert p.site_name == "S"
        assert p.type == "article"
        assert p.url == "http://u.com"
        assert p.locale == "en_US"
        assert p.twitter_card == "summary_large_image"


# ---------------------------------------------------------------------------
# Boundary / defensive
# ---------------------------------------------------------------------------

class TestBoundaryAndDefensive:
    def test_long_content_preserved(self, gen):
        long = "x" * 10000
        html = f'<meta property="og:title" content="{long}">'
        assert len(gen.generate(html).title) == 10000

    def test_single_char_content(self, gen):
        assert gen.generate('<meta property="og:title" content="x">').title == "x"

    def test_html_entities_decoded(self, gen):
        html = '<meta property="og:title" content="A &amp; B &lt;C&gt;">'
        assert gen.generate(html).title == "A & B <C>"

    def test_malformed_html_no_crash(self, gen):
        # unclosed tag: must not raise, must degrade gracefully
        p = gen.generate('<html><head><meta property="og:title" content="unclosed')
        assert isinstance(p, LinkPreview)

    def test_whitespace_stripped_from_all_fields(self, gen):
        html = (
            '<meta property="og:title" content="  T  ">'
            '<meta property="og:description" content="  D  ">'
            '<meta property="og:site_name" content="  S  ">'
        )
        p = gen.generate(html)
        assert p.title == "T"
        assert p.description == "D"
        assert p.site_name == "S"


# ---------------------------------------------------------------------------
# End-to-end: installed CLI entry point + module reachable via installed pkg
# ---------------------------------------------------------------------------

class TestEndToEndCLI:
    def test_cli_entry_point_runs_and_module_reachable(self):
        """Run the installed CLI entry point and confirm link_preview is
        importable through the installed package (library module, no
        dedicated CLI subcommand)."""
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "Personal Index" in proc.stdout

        # module reachable through the installed package path
        import personal_index

        from personal_index.link_preview import LinkPreviewGenerator

        assert personal_index.__file__ is not None
        p = LinkPreviewGenerator().generate("<title>E2E</title>")
        assert p.title == "E2E"
