"""
Adversarial deep tests for personal_index.content_importer (never-probed subsystem).

Cycle 219 (VALIDATOR). The module is not CLI-wired (the CLI `import` command is
wired to the separate file-oriented personal_index/importer.py `Importer`), so
the end-to-end CLI smoke run exercises the installed entry point directly.

The docs contract (docs/content-importer.md) documents four "contract holes":
  1. Inconsistent item shape across formats — RESOLVED (ARCH-24): every format
     now routes through _normalize_items and returns the uniform 6-key set.
  2. batch_import is untyped and aborts on first error (no partial result).
  3. _import_rss uses stdlib ElementTree (not defusedxml); empty/malformed XML
     raises ET.ParseError.
  4. A bare JSON scalar (neither object nor array) is not wrapped: a number/
     null reaches _normalize_items as a non-list and raises TypeError; a bare
     JSON string is a valid list-iterable of chars and yields [].

These tests pin the ACTUAL behavior (which matches the docs on all four holes)
as regression armor. No defect was found in this cycle.
"""

from __future__ import annotations

import subprocess
import sys
from xml.etree import ElementTree as ET

import pytest

from personal_index.content_importer import ContentImporter

# The uniform key set every normalized item must carry (docs contract hole 1,
# RESOLVED). This is the load-bearing VERIFY of the RESOLVED contract hole.
UNIFORM_KEYS = {"title", "description", "link", "id", "tags", "date"}


def assert_uniform(items: list[dict]) -> None:
    """Every item carries EXACTLY the uniform 6-key set (no more, no less)."""
    for item in items:
        assert set(item.keys()) == UNIFORM_KEYS, (
            f"item key set {sorted(item.keys())} != uniform {sorted(UNIFORM_KEYS)}"
        )


@pytest.fixture
def imp() -> ContentImporter:
    return ContentImporter()


# ---------------------------------------------------------------------------
# Contract hole 1 (RESOLVED): uniform key set across ALL five formats
# ---------------------------------------------------------------------------
class TestUniformKeySet:
    def test_json_array_uniform(self, imp):
        assert_uniform(imp.import_content('[{"title": "a"}, {"title": "b"}]', "json"))

    def test_json_object_wrapped_uniform(self, imp):
        assert_uniform(imp.import_content('{"title": "solo"}', "json"))

    def test_html_article_uniform(self, imp):
        assert_uniform(
            imp.import_content(
                '<article><h2>T</h2><p>D</p><a href="http://x">L</a></article>', "html"
            )
        )

    def test_html_fallback_uniform(self, imp):
        # Fallback path (no <article>) previously lacked `link`; after normalize
        # it must carry the uniform set with link defaulting to "".
        items = imp.import_content("<h2>H</h2><p>P</p>", "html")
        assert_uniform(items)
        assert items[0]["link"] == ""

    def test_markdown_uniform(self, imp):
        assert_uniform(imp.import_content("# Title\nbody", "markdown"))

    def test_rss_uniform(self, imp):
        assert_uniform(
            imp.import_content(
                "<rss><channel><item><title>R</title><link>http://r</link>"
                "<description>D</description></item></channel></rss>",
                "rss",
            )
        )

    def test_csv_uniform(self, imp):
        # Ad-hoc header columns are dropped; the uniform set is what remains.
        assert_uniform(imp.import_content("title,link,extra\nA,http://a,e1", "csv"))

    def test_batch_import_all_sources_uniform(self, imp):
        items = imp.batch_import(
            [
                ('[{"title": "j"}]', "json"),
                ("<h2>H</h2><p>P</p>", "html"),
                ("# M\nb", "markdown"),
                ("title\nC", "csv"),
            ]
        )
        assert_uniform(items)
        assert [it["title"] for it in items] == ["j", "H", "M", "C"]


# ---------------------------------------------------------------------------
# Format normalization + guard path
# ---------------------------------------------------------------------------
class TestFormatNormalization:
    @pytest.mark.parametrize("fmt", ["JSON", "  json  ", "Json", "jSoN"])
    def test_case_and_whitespace_normalized(self, imp, fmt):
        items = imp.import_content('[{"title": "x"}]', fmt)
        assert items[0]["title"] == "x"

    def test_whitespace_only_fmt_raises(self, imp):
        with pytest.raises(ValueError, match="Unsupported format"):
            imp.import_content("[]", "   ")

    def test_unsupported_fmt_raises_valueerror(self, imp):
        with pytest.raises(ValueError, match="Unsupported format: yaml"):
            imp.import_content("x", "yaml")

    def test_unsupported_fmt_message_lists_supported(self, imp):
        with pytest.raises(ValueError) as exc:
            imp.import_content("x", "xml")
        for fmt in ContentImporter.SUPPORTED_FORMATS:
            assert fmt in str(exc.value)

    def test_supported_formats_tuple(self):
        assert ContentImporter.SUPPORTED_FORMATS == ("json", "html", "markdown", "rss", "csv")


# ---------------------------------------------------------------------------
# JSON handler — adversarial inputs
# ---------------------------------------------------------------------------
class TestJsonAdversarial:
    def test_empty_list(self, imp):
        assert imp.import_content("[]", "json") == []

    def test_malformed_raises_valueerror(self, imp):
        with pytest.raises(ValueError, match="Malformed JSON"):
            imp.import_content("{bad", "json")

    def test_none_data_raises_typeerror(self, imp):
        # json.loads(None) is not a JSONDecodeError; it raises TypeError.
        with pytest.raises(TypeError):
            imp.import_content(None, "json")  # type: ignore[arg-type]

    def test_scalar_number_raises_typeerror(self, imp):
        # Contract hole 4: a bare JSON number is not wrapped and reaches
        # _normalize_items as a non-list -> TypeError from iteration.
        with pytest.raises(TypeError):
            imp.import_content("123", "json")

    def test_scalar_null_raises_typeerror(self, imp):
        # Contract hole 4: null -> None, non-list -> TypeError.
        with pytest.raises(TypeError):
            imp.import_content("null", "json")

    def test_scalar_string_yields_empty(self, imp):
        # Contract hole 4 (actual behavior): a bare JSON string is a valid
        # iterable of chars, each char is a non-dict -> skipped -> [].
        assert imp.import_content('"hi"', "json") == []

    def test_non_dict_entries_in_array_skipped(self, imp):
        items = imp.import_content('[1, 2, {"title": "ok"}, null]', "json")
        assert [it["title"] for it in items] == ["ok"]

    def test_missing_fields_get_defaults(self, imp):
        item = imp.import_content('[{"title": "t"}]', "json")[0]
        assert item["description"] == ""
        assert item["link"] == ""
        assert item["tags"] == []
        assert item["date"] is None

    def test_missing_title_defaults_untitled(self, imp):
        item = imp.import_content('[{"description": "d"}]', "json")[0]
        assert item["title"] == "Untitled"

    def test_tags_preserved(self, imp):
        item = imp.import_content('[{"title": "t", "tags": ["a", "b"]}]', "json")[0]
        assert item["tags"] == ["a", "b"]

    def test_date_preserved(self, imp):
        item = imp.import_content('[{"title": "t", "date": "2026-01-01"}]', "json")[0]
        assert item["date"] == "2026-01-01"

    def test_unicode_title_preserved(self, imp):
        item = imp.import_content('[{"title": "Привет 世界 🎉"}]', "json")[0]
        assert item["title"] == "Привет 世界 🎉"

    def test_duplicate_titles_both_kept(self, imp):
        items = imp.import_content('[{"title": "dup"}, {"title": "dup"}]', "json")
        assert [it["title"] for it in items] == ["dup", "dup"]
        assert items[0]["id"] != items[1]["id"]


# ---------------------------------------------------------------------------
# HTML handler — adversarial inputs
# ---------------------------------------------------------------------------
class TestHtmlAdversarial:
    def test_empty_string(self, imp):
        assert imp.import_content("", "html") == []

    def test_no_articles_no_headings(self, imp):
        assert imp.import_content("<div>nope</div>", "html") == []

    def test_empty_article_defaults(self, imp):
        item = imp.import_content("<article></article>", "html")[0]
        assert item["title"] == "Untitled"
        assert item["description"] == ""
        assert item["link"] == ""

    def test_article_without_link(self, imp):
        item = imp.import_content("<article><h2>T</h2><p>D</p></article>", "html")[0]
        assert item["title"] == "T"
        assert item["description"] == "D"
        assert item["link"] == ""

    def test_fallback_more_headings_than_paragraphs(self, imp):
        # Index pairing: only the first heading gets a paragraph; the rest "".
        items = imp.import_content(
            "<h2>A</h2><h2>B</h2><h2>C</h2><p>only-one</p>", "html"
        )
        assert [it["description"] for it in items] == ["only-one", "", ""]

    def test_fallback_strips_inner_tags(self, imp):
        item = imp.import_content("<h2><span>Hi</span></h2><p>x</p>", "html")[0]
        assert item["title"] == "Hi"

    def test_multiple_articles(self, imp):
        html = (
            '<article><h2>A</h2><p>a</p></article>'
            '<article><h2>B</h2><p>b</p></article>'
        )
        items = imp.import_content(html, "html")
        assert [it["title"] for it in items] == ["A", "B"]

    def test_unicode(self, imp):
        item = imp.import_content("<article><h2>Привет</h2><p>мир</p></article>", "html")[0]
        assert item["title"] == "Привет"
        assert item["description"] == "мир"


# ---------------------------------------------------------------------------
# Markdown handler — adversarial inputs
# ---------------------------------------------------------------------------
class TestMarkdownAdversarial:
    def test_empty_string(self, imp):
        assert imp.import_content("", "markdown") == []

    def test_no_headings(self, imp):
        # Lines before any heading are dropped (no current_item yet).
        assert imp.import_content("just text\nno heading", "markdown") == []

    def test_linked_heading(self, imp):
        item = imp.import_content("# [My Title](http://x)\nbody", "markdown")[0]
        assert item["title"] == "My Title"
        assert item["link"] == "http://x"

    def test_plain_heading_empty_link(self, imp):
        item = imp.import_content("## Plain\nbody", "markdown")[0]
        assert item["title"] == "Plain"
        assert item["link"] == ""

    def test_multiline_description(self, imp):
        item = imp.import_content("# T\nline1\nline2\n", "markdown")[0]
        assert item["description"] == "line1\nline2"

    def test_multiple_sections(self, imp):
        items = imp.import_content("# A\na1\n## B\nb1\nb2", "markdown")
        assert [it["title"] for it in items] == ["A", "B"]
        assert items[1]["description"] == "b1\nb2"

    def test_heading_only_no_description(self, imp):
        item = imp.import_content("# T", "markdown")[0]
        assert item["description"] == ""

    def test_unicode(self, imp):
        item = imp.import_content("# Привет 世界\nлиния", "markdown")[0]
        assert item["title"] == "Привет 世界"
        assert item["description"] == "линия"


# ---------------------------------------------------------------------------
# CSV handler — adversarial inputs
# ---------------------------------------------------------------------------
class TestCsvAdversarial:
    def test_empty_string(self, imp):
        assert imp.import_content("", "csv") == []

    def test_header_only_no_rows(self, imp):
        assert imp.import_content("title,link", "csv") == []

    def test_empty_values_dropped(self, imp):
        item = imp.import_content("title,link\nA,,", "csv")[0]
        assert item["title"] == "A"
        assert item["link"] == ""

    def test_adhoc_columns_dropped_after_normalize(self, imp):
        item = imp.import_content("title,extra\nA,e1", "csv")[0]
        assert set(item.keys()) == UNIFORM_KEYS
        assert "extra" not in item

    def test_missing_id_minted(self, imp):
        item = imp.import_content("title\nA", "csv")[0]
        assert item["id"] == "1"

    def test_provided_id_preserved(self, imp):
        item = imp.import_content("title,id\nA,myid", "csv")[0]
        assert item["id"] == "myid"

    def test_multiple_rows(self, imp):
        items = imp.import_content("title\nA\nB\nC", "csv")
        assert [it["title"] for it in items] == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# RSS handler — adversarial inputs (contract hole 3: stdlib ElementTree)
# ---------------------------------------------------------------------------
class TestRssAdversarial:
    def test_empty_string_raises_parseerror(self, imp):
        # Contract hole 3: stdlib ET.fromstring on empty -> ParseError.
        with pytest.raises(ET.ParseError):
            imp.import_content("", "rss")

    def test_truncated_xml_raises_parseerror(self, imp):
        with pytest.raises(ET.ParseError):
            imp.import_content("<rss><channel>", "rss")

    def test_no_channel(self, imp):
        assert imp.import_content("<rss></rss>", "rss") == []

    def test_missing_guid_minted(self, imp):
        item = imp.import_content(
            "<rss><channel><item><title>R</title></item></channel></rss>", "rss"
        )[0]
        assert item["title"] == "R"
        assert item["id"] == "1"  # minted, not a guid

    def test_guid_preserved_as_id(self, imp):
        item = imp.import_content(
            "<rss><channel><item><title>R</title><guid>g1</guid></item></channel></rss>",
            "rss",
        )[0]
        assert item["id"] == "g1"

    def test_missing_title_defaults_untitled(self, imp):
        item = imp.import_content(
            "<rss><channel><item><link>http://x</link></item></channel></rss>", "rss"
        )[0]
        assert item["title"] == "Untitled"

    def test_multiple_items(self, imp):
        xml = (
            "<rss><channel>"
            "<item><title>A</title></item>"
            "<item><title>B</title></item>"
            "</channel></rss>"
        )
        items = imp.import_content(xml, "rss")
        assert [it["title"] for it in items] == ["A", "B"]


# ---------------------------------------------------------------------------
# batch_import — contract hole 2 (untyped, aborts on first error)
# ---------------------------------------------------------------------------
class TestBatchImport:
    def test_empty_list(self, imp):
        assert imp.batch_import([]) == []

    def test_single_source(self, imp):
        items = imp.batch_import([('[{"title": "a"}]', "json")])
        assert [it["title"] for it in items] == ["a"]

    def test_concatenates_in_order(self, imp):
        items = imp.batch_import(
            [('[{"title": "a"}]', "json"), ('[{"title": "b"}]', "json")]
        )
        assert [it["title"] for it in items] == ["a", "b"]

    def test_aborts_on_first_error_discards_earlier(self, imp):
        # Contract hole 2: a bad source raises and all earlier items are lost.
        with pytest.raises(ValueError, match="Malformed JSON"):
            imp.batch_import([('[{"title": "a"}]', "json"), ("{bad", "json")])

    def test_unsupported_fmt_in_middle_aborts(self, imp):
        with pytest.raises(ValueError, match="Unsupported format: yaml"):
            imp.batch_import([('[{"title": "a"}]', "json"), ("x", "yaml")])


# ---------------------------------------------------------------------------
# _next_id / idempotence / instance independence
# ---------------------------------------------------------------------------
class TestIdCounter:
    def test_fresh_instance_starts_at_one(self):
        item = ContentImporter().import_content('[{"title": "x"}]', "json")[0]
        assert item["id"] == "1"

    def test_counter_increments_across_calls(self):
        # The docs pin that ids are unique, monotonically increasing, and start
        # from 1. The exact counter rate is an implementation detail (the eager
        # default in dict.get("id", str(self._next_id())) plus the double
        # _normalize_items call advance the counter faster than one per item),
        # so we assert the observable guarantees, not the exact rate.
        imp = ContentImporter()
        first = imp.import_content('[{"title": "a"}]', "json")[0]["id"]
        second = imp.import_content('[{"title": "b"}]', "json")[0]["id"]
        assert first == "1"
        assert int(second) > int(first)

    def test_instances_independent(self):
        a = ContentImporter().import_content('[{"title": "x"}]', "json")[0]["id"]
        b = ContentImporter().import_content('[{"title": "y"}]', "json")[0]["id"]
        assert a == "1"
        assert b == "1"

    def test_same_input_twice_same_shape_different_id(self):
        imp = ContentImporter()
        a = imp.import_content('[{"title": "x"}]', "json")[0]
        b = imp.import_content('[{"title": "x"}]', "json")[0]
        assert set(a.keys()) == set(b.keys()) == UNIFORM_KEYS
        assert a["id"] != b["id"]


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (content_importer is NOT CLI-wired; the CLI `import`
# command uses the separate file-oriented personal_index/importer.py).
# ---------------------------------------------------------------------------
class TestCliSmoke:
    def test_cli_version_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "personal-index" in result.stdout

    def test_cli_import_command_exists(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "import", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Import local files" in result.stdout
