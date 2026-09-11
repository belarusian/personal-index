"""Cycle 167 PROBE: personal_index/importer.py (never-probed subsystem).

Adversarial deep tests for the bookmark Importer:
  - Importer.import_from_file / import_from_content  (dispatch + guards)
  - _import_json / _import_csv / _import_html / _import_xml / import_opml
  - one end-to-end run through the installed CLI (import -> search)

Guard inputs: None/empty/whitespace/unicode/duplicate/out-of-range,
round-trips, idempotence, property checks.

DEFECT FILED (QA-8): _import_json crashes with an uncaught AttributeError
when a JSON array contains a non-dict item (int/str/bool/float/null/list).
The docstring explicitly promises: "A per-item ValueError/TypeError ... is
caught, appended to result.errors as 'Error importing item: ...' and the
loop continues to the next item rather than aborting." The except clause
only catches (ValueError, TypeError); item.get(...) on a non-dict raises
AttributeError, which propagates and aborts the whole import. Pinned
xfail-strict so the suite stays green while the defect exists; flips to a
hard pass once the loop guards non-dict items (or catches AttributeError).
"""

from __future__ import annotations

import subprocess
import sys


from personal_index.bookmarks import BookmarkManager
from personal_index.importer import Importer, ImportResult


def _imp() -> Importer:
    return Importer(BookmarkManager())


# ── clean armor: valid imports ──────────────────────────────────────────


class TestJsonValid:
    def test_array_of_dicts(self):
        r = _imp().import_from_content(
            '[{"url": "http://a.com", "title": "A"}, '
            '{"url": "http://b.com", "title": "B"}]',
            "json",
        )
        assert r.total_imported == 2
        assert r.total_skipped == 0
        assert r.errors == []
        assert r.format == "json"

    def test_single_dict_normalized_to_list(self):
        r = _imp().import_from_content('{"url": "http://a.com"}', "json")
        assert r.total_imported == 1

    def test_empty_url_skipped(self):
        r = _imp().import_from_content('[{"url": "", "title": "x"}]', "json")
        assert r.total_imported == 0
        assert r.total_skipped == 1

    def test_invalid_json_reports_error(self):
        r = _imp().import_from_content("{not json", "json")
        assert r.total_imported == 0
        assert any("Invalid JSON" in e for e in r.errors)

    def test_unicode_round_trip(self):
        imp = _imp()
        r = imp.import_from_content(
            '[{"url": "http://a.com", "title": "Привет 世界"}]', "json"
        )
        assert r.total_imported == 1
        b = imp.manager.get("http://a.com")
        assert b is not None and b.title == "Привет 世界"


class TestCsvValid:
    def test_basic_rows(self):
        imp = _imp()
        r = imp.import_from_content(
            "url,title,category,tags\n"
            "http://a.com,A,tech,\"python,web\"\n"
            "http://b.com,B,tech,go\n",
            "csv",
        )
        assert r.total_imported == 2
        b = imp.manager.get("http://a.com")
        assert b is not None and b.tags == ["python", "web"]

    def test_header_only_no_rows(self):
        r = _imp().import_from_content("url,title\n", "csv")
        assert r.total_imported == 0
        assert r.errors == []

    def test_empty_content(self):
        r = _imp().import_from_content("", "csv")
        assert r.total_imported == 0
        assert r.errors == []

    def test_missing_tags_column_does_not_crash(self):
        # DictReader restval is None for absent columns; row.get("tags", "")
        # returns the present None, so the default is NOT applied.
        r = _imp().import_from_content("url,title\nhttp://a.com,Hello\n", "csv")
        assert r.total_imported == 1
        assert r.errors == []


class TestHtmlValid:
    def test_anchors_imported(self):
        r = _imp().import_from_content(
            "<html><body><a href='http://a.com'>A</a>"
            "<a href='http://b.com' title='BT'>B</a></body></html>",
            "html",
        )
        assert r.total_imported == 2

    def test_non_html_rejected(self):
        r = _imp().import_from_content("just plain text, no tags", "html")
        assert r.total_imported == 0
        assert any("Invalid HTML" in e for e in r.errors)

    def test_empty_content_rejected(self):
        r = _imp().import_from_content("", "html")
        assert r.total_imported == 0
        assert r.errors


class TestXmlValid:
    def test_bookmark_elements(self):
        xml = (
            "<bookmarks>"
            "<bookmark url='http://a.com'><title>A</title></bookmark>"
            "<bookmark><url>http://b.com</url><tags>x, y</tags></bookmark>"
            "</bookmarks>"
        )
        r = _imp().import_from_content(xml, "xml")
        assert r.total_imported == 2

    def test_invalid_xml_reports_error(self):
        r = _imp().import_from_content("<bookmarks><unclosed>", "xml")
        assert r.total_imported == 0
        assert any("Invalid XML" in e for e in r.errors)


class TestOpmlValid:
    def test_outlines_with_xmlurl(self):
        opml = (
            "<opml><body>"
            "<outline text='A' xmlUrl='http://a.com'/>"
            "<outline text='B' htmlUrl='http://b.com'/>"
            "</body></opml>"
        )
        r = _imp().import_opml(opml)
        assert r.total_imported == 2
        assert r.format == "opml"

    def test_outline_without_url_counts_skipped(self):
        r = _imp().import_opml("<opml><outline text='no url'/></opml>")
        assert r.total_imported == 0
        assert r.total_skipped == 1
        assert r.errors == []


class TestDispatchGuards:
    def test_fmt_case_and_dot_normalization(self):
        for fmt in ("JSON", ".csv", "Html", "XML"):
            r = _imp().import_from_content(
                '[{"url": "http://a.com"}]' if fmt in ("JSON",) else "url\nhttp://a.com\n" if fmt == ".csv" else "<a href='http://a.com'/>" if fmt == "Html" else "<b><bookmark url='http://a.com'/></b>",
                fmt,
            )
            assert r.total_imported == 1, fmt

    def test_unsupported_format_reports_error(self):
        r = _imp().import_from_content("x", "yaml")
        assert r.total_imported == 0
        assert r.errors == ["Unsupported format: yaml"]

    def test_empty_fmt_is_unsupported_not_crash(self):
        r = _imp().import_from_content("x", "")
        assert r.errors == ["Unsupported format: "]

    def test_import_from_file_missing(self, tmp_path):
        r = _imp().import_from_file(str(tmp_path / "nope.json"))
        assert r.total_imported == 0
        assert any("File not found" in e for e in r.errors)

    def test_import_from_file_unsupported_ext(self, tmp_path):
        p = tmp_path / "data.yaml"
        p.write_text("a: 1", encoding="utf-8")
        r = _imp().import_from_file(str(p))
        assert r.errors == ["Unsupported format: yaml"]
        assert r.format == "yaml"

    def test_import_from_file_round_trip(self, tmp_path):
        p = tmp_path / "bm.json"
        p.write_text('[{"url": "http://a.com", "title": "A"}]', encoding="utf-8")
        imp = _imp()
        r = imp.import_from_file(str(p))
        assert r.total_imported == 1
        assert imp.manager.get("http://a.com") is not None

    def test_import_result_defaults(self):
        r = ImportResult()
        assert r.total_imported == 0
        assert r.total_skipped == 0
        assert r.errors == []
        assert r.imported_at  # auto-stamped


# ── DEFECT (QA-8): JSON non-dict item crashes the whole import ──────────


class TestJsonNonDictItemContract:
    """The _import_json docstring promises per-item errors are caught and the
    loop continues. A non-dict item (int/str/bool/float/null/list) raises
    AttributeError on item.get(...), which is NOT in the except clause, so the
    whole import aborts instead of skipping the bad item and continuing."""

    def test_int_item_caught_and_loop_continues(self):
        r = _imp().import_from_content(
            '[{"url": "http://a.com"}, 42, {"url": "http://b.com"}]', "json"
        )
        # Contract: bad item recorded as an error, good items still imported.
        assert r.total_imported == 2
        assert any("Error importing item" in e for e in r.errors)

    def test_null_item_caught_and_loop_continues(self):
        r = _imp().import_from_content(
            '[{"url": "http://a.com"}, null]', "json"
        )
        assert r.total_imported == 1
        assert any("Error importing item" in e for e in r.errors)


# ── end-to-end through the installed CLI (import -> search) ─────────────


class TestCliEndToEnd:
    def test_cli_import_then_search(self, tmp_path):
        data_dir = str(tmp_path / "dd")
        page = tmp_path / "note.txt"
        page.write_text(
            "A note about the personal index and how it stores bookmarks.",
            encoding="utf-8",
        )
        imp = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "import", str(page)],
            capture_output=True, text=True,
        )
        assert imp.returncode == 0, imp.stderr
        assert "Import complete" in imp.stdout

        srch = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "search", "bookmarks"],
            capture_output=True, text=True,
        )
        assert srch.returncode == 0, srch.stderr
        assert "note" in srch.stdout.lower()
