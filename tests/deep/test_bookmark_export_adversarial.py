"""Adversarial deep tests for personal_index.bookmark_export.

Contract source: module docstrings (personal_index/bookmark_export.py).
This module has NO dedicated docs page, so the docstrings are the contract.

Key docstring claims under test:
  * ``export_opml``: "Produces a **valid OPML 2.0 document** with a head
    section containing metadata and a body section containing outline
    elements for each bookmark."
  * ``export_html``: "Produces a **standard Netscape bookmark file** that
    can be imported into most browsers."
  * ``export``: fmt is "case-insensitive"; returns None for unsupported.
  * ``export_to_file``: format auto-detected from extension; returns a
    ``BookmarkExportResult`` on success, or a result with errors on failure.

DEFECT (QA-32): ``export_opml`` inserts ``b.url`` RAW into the
``htmlUrl="{b.url}"`` attribute (only the title is escaped via
``_escape_xml``). A URL containing ``&`` (e.g. a query string
``?a=1&b=2``), ``<``, or ``"`` therefore produces XML that is NOT
well-formed, contradicting the "valid OPML 2.0 document" claim. The same
raw-URL insertion in ``export_html`` breaks the ``HREF`` attribute on a
``"`` in the URL. Pinned xfail-strict below.
"""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from personal_index.bookmark_export import (
    BookmarkExporter,
    BookmarkExportResult,
)
from personal_index.bookmarks import Bookmark


def _bm(url: str = "https://example.com/a", title: str = "T", **kw) -> Bookmark:
    return Bookmark(url=url, title=title, **kw)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


def test_export_json_empty_list_is_empty_array():
    assert BookmarkExporter([]).export_json() == "[]"


def test_export_json_single_round_trips():
    b = _bm("https://example.com/a", "My Page", category="tech", tags=["x", "y"])
    out = BookmarkExporter([b]).export_json()
    data = json.loads(out)
    assert data == [b.to_dict()]


def test_export_json_multiple_preserves_order():
    b1 = _bm("https://example.com/1", "One")
    b2 = _bm("https://example.com/2", "Two")
    data = json.loads(BookmarkExporter([b1, b2]).export_json())
    assert [d["url"] for d in data] == ["https://example.com/1", "https://example.com/2"]


def test_export_json_unicode_round_trips():
    b = _bm("https://example.com/a", "Caf\u00e9 \u4f60\u597d")
    data = json.loads(BookmarkExporter([b]).export_json())
    assert data[0]["title"] == "Caf\u00e9 \u4f60\u597d"


def test_export_json_duplicate_bookmarks_both_present():
    b = _bm("https://example.com/a", "Dup")
    data = json.loads(BookmarkExporter([b, b]).export_json())
    assert len(data) == 2


def test_export_json_is_pretty_printed():
    out = BookmarkExporter([_bm()]).export_json()
    assert "\n" in out and out.startswith("[")


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------


def test_export_html_empty_list_has_scaffold():
    out = BookmarkExporter([]).export_html()
    assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in out
    assert "<DL><p>" in out
    assert "</DL>" in out


def test_export_html_escapes_title_special_chars():
    b = _bm("https://example.com/a", "A & B <C> \"D\"")
    out = BookmarkExporter([b]).export_html()
    assert "A &amp; B &lt;C&gt; &quot;D&quot;" in out
    # The raw unescaped title must NOT appear.
    assert "A & B <C>" not in out


def test_export_html_empty_title_falls_back_to_url():
    b = _bm("https://example.com/fallback", "")
    out = BookmarkExporter([b]).export_html()
    assert "https://example.com/fallback" in out


def test_export_html_contains_href_and_add_date():
    out = BookmarkExporter([_bm("https://example.com/a", "T")]).export_html()
    assert 'HREF="https://example.com/a"' in out
    assert "ADD_DATE=" in out


def test_export_html_unicode_title_round_trips():
    b = _bm("https://example.com/a", "Caf\u00e9")
    out = BookmarkExporter([b]).export_html()
    assert "Caf\u00e9" in out


# ---------------------------------------------------------------------------
# OPML export
# ---------------------------------------------------------------------------


def test_export_opml_empty_list_is_well_formed():
    out = BookmarkExporter([]).export_opml()
    ET.fromstring(out)  # must not raise
    assert '<opml version="2.0">' in out


def test_export_opml_plain_url_is_well_formed():
    out = BookmarkExporter([_bm("https://example.com/a", "T")]).export_opml()
    ET.fromstring(out)
    assert 'htmlUrl="https://example.com/a"' in out


def test_export_opml_escapes_title_special_chars():
    b = _bm("https://example.com/a", "A & B <C> \"D\" 'E'")
    out = BookmarkExporter([b]).export_opml()
    ET.fromstring(out)  # title escaping keeps it well-formed
    assert "A &amp; B &lt;C&gt; &quot;D&quot; &apos;E&apos;" in out


def test_export_opml_multiple_outlines():
    out = BookmarkExporter([_bm("https://example.com/1"), _bm("https://example.com/2")]).export_opml()
    root = ET.fromstring(out)
    outlines = root.findall(".//outline")
    assert len(outlines) == 2


def test_export_opml_unicode_title_round_trips():
    b = _bm("https://example.com/a", "Caf\u00e9 \u4f60\u597d")
    out = BookmarkExporter([b]).export_opml()
    root = ET.fromstring(out)
    assert root.find(".//outline").get("text") == "Caf\u00e9 \u4f60\u597d"


# ---------------------------------------------------------------------------
# export() dispatch
# ---------------------------------------------------------------------------


def test_export_dispatch_all_three_formats():
    ex = BookmarkExporter([_bm()])
    assert ex.export("json") is not None
    assert ex.export("html") is not None
    assert ex.export("opml") is not None


def test_export_dispatch_is_case_insensitive():
    ex = BookmarkExporter([_bm()])
    assert ex.export("JSON") is not None
    assert ex.export("Html") is not None
    assert ex.export("OPML") is not None


def test_export_dispatch_unsupported_returns_none():
    assert BookmarkExporter([_bm()]).export("txt") is None
    assert BookmarkExporter([_bm()]).export("") is None


# ---------------------------------------------------------------------------
# export_to_file
# ---------------------------------------------------------------------------


def test_export_to_file_auto_detects_json(tmp_path):
    p = tmp_path / "out.json"
    res = BookmarkExporter([_bm()]).export_to_file(str(p))
    assert res.errors == []
    assert res.format == "json"
    assert res.bookmark_count == 1
    assert json.loads(p.read_text(encoding="utf-8"))


def test_export_to_file_auto_detects_opml(tmp_path):
    p = tmp_path / "out.opml"
    res = BookmarkExporter([_bm()]).export_to_file(str(p))
    assert res.errors == []
    assert res.format == "opml"
    ET.fromstring(p.read_text(encoding="utf-8"))


def test_export_to_file_explicit_fmt_overrides_extension(tmp_path):
    p = tmp_path / "out.json"
    res = BookmarkExporter([_bm()]).export_to_file(str(p), fmt="opml")
    assert res.format == "opml"
    ET.fromstring(p.read_text(encoding="utf-8"))


def test_export_to_file_unsupported_extension_reports_error(tmp_path):
    p = tmp_path / "out.xyz"
    res = BookmarkExporter([_bm()]).export_to_file(str(p))
    assert res.errors
    assert "Unsupported format" in res.errors[0]
    assert not p.exists()


def test_export_to_file_unsupported_fmt_reports_error(tmp_path):
    p = tmp_path / "out.json"
    res = BookmarkExporter([_bm()]).export_to_file(str(p), fmt="csv")
    assert res.errors
    assert "Unsupported format" in res.errors[0]


def test_export_to_file_write_failure_reports_error(tmp_path):
    # A path whose parent does not exist -> OSError on open.
    res = BookmarkExporter([_bm()]).export_to_file(str(tmp_path / "nope" / "out.json"))
    assert res.errors
    assert "Failed to write file" in res.errors[0]


def test_export_to_file_empty_bookmarks_still_succeeds(tmp_path):
    p = tmp_path / "out.json"
    res = BookmarkExporter([]).export_to_file(str(p))
    assert res.errors == []
    assert res.bookmark_count == 0
    assert json.loads(p.read_text(encoding="utf-8")) == []


# ---------------------------------------------------------------------------
# BookmarkExportResult
# ---------------------------------------------------------------------------


def test_result_default_exported_at_is_set():
    res = BookmarkExportResult()
    assert res.exported_at  # __post_init__ fills it


def test_result_default_fields():
    res = BookmarkExportResult()
    assert res.format == ""
    assert res.bookmark_count == 0
    assert res.errors == []


def test_result_idempotent_post_init():
    res = BookmarkExportResult(exported_at="2026-01-01T00:00:00+00:00")
    assert res.exported_at == "2026-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# DEFECT (QA-32): raw URL insertion breaks OPML well-formedness
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "QA-32: export_opml inserts b.url RAW into htmlUrl=\"{b.url}\" "
        "(only the title is escaped). A URL with '&' (a normal query string) "
        "produces XML that is not well-formed, contradicting the docstring "
        "claim 'Produces a valid OPML 2.0 document'."
    ),
)
def test_export_opml_url_with_ampersand_is_well_formed():
    b = _bm("https://example.com/search?q=hello&lang=en", "T")
    out = BookmarkExporter([b]).export_opml()
    ET.fromstring(out)  # must parse as valid XML


@pytest.mark.xfail(
    strict=True,
    reason=(
        "QA-32: export_html inserts b.url RAW into HREF=\"{b.url}\". A URL "
        "containing a double-quote breaks the attribute, contradicting the "
        "'standard Netscape bookmark file' claim."
    ),
)
def test_export_html_url_with_double_quote_keeps_attribute_intact():
    b = _bm('https://example.com/?x="y"', "T")
    out = BookmarkExporter([b]).export_html()
    # The HREF attribute must remain a single well-formed attribute.
    assert 'HREF="https://example.com/?x=&quot;y&quot;"' in out


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (module not wired to a subcommand; status is the
# installed-CLI entry point)
# ---------------------------------------------------------------------------


def test_cli_status_smoke():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "status"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Personal Index Status" in proc.stdout
