"""Adversarial deep tests for personal_index.export.Exporter.

Contract source: personal_index/export.py docstrings and ARCH-81 fix.
Tests edge cases: empty manager, unicode/special chars, round-trip,
idempotence, format auto-detection, filtered export, and HTML/XML escaping.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from personal_index.bookmarks import Bookmark, BookmarkManager
from personal_index.export import Exporter, ExportResult


def _make_manager() -> BookmarkManager:
    m = BookmarkManager()
    m.add(Bookmark(url="http://example.com/a", title="A", category="tech", tags=["python"], is_favorite=True))
    m.add(Bookmark(url="http://example.com/b", title="B & < > \" '", category="news", description="Desc with & < > \" '", tags=["news"]))
    m.add(Bookmark(url="http://example.com/ünîcödé", title="Üñîçødé", category="misc"))
    return m


def test_export_result_defaults():
    r = ExportResult()
    assert r.total_exported == 0
    assert r.output_path == ""
    assert r.format == ""
    assert r.errors == []
    assert r.exported_at != ""


def test_exporter_manager_property():
    m = BookmarkManager()
    e = Exporter(m)
    assert e.manager is m
    # default manager
    e2 = Exporter()
    assert isinstance(e2.manager, BookmarkManager)


def test_export_to_content_json_empty():
    e = Exporter(BookmarkManager())
    content = e.export_to_content("json")
    assert content == "[]"
    data = json.loads(content)
    assert data == []


def test_export_to_content_json_roundtrip():
    m = _make_manager()
    e = Exporter(m)
    content = e.export_to_content("json")
    data = json.loads(content)
    assert len(data) == 3
    # unicode preserved
    titles = [d["title"] for d in data]
    assert "Üñîçødé" in titles


def test_export_to_content_csv_header_and_rows():
    m = _make_manager()
    e = Exporter(m)
    content = e.export_to_content("csv")
    lines = content.splitlines()
    assert lines[0].startswith("url,title,description")
    # at least 3 data rows
    assert len(lines) >= 4


def test_export_to_content_html_balanced_dl():
    m = _make_manager()
    e = Exporter(m)
    content = e.export_to_content("html")
    assert content.count("<DL>") == 1
    assert content.count("</DL>") == 1
    # DOCTYPE present
    assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in content


def test_export_to_content_html_escapes_special_chars():
    m = BookmarkManager()
    m.add(Bookmark(url="http://x.com", title='A & < > " \''))
    e = Exporter(m)
    content = e.export_to_content("html")
    # HTML escape: & -> &amp;, < -> &lt;, > -> &gt;, " -> &quot;
    assert "&amp;" in content
    assert "&lt;" in content
    assert "&gt;" in content
    assert "&quot;" in content
    # No raw < > in title
    assert "A & < >" not in content


def test_export_to_content_xml_escapes():
    m = BookmarkManager()
    m.add(Bookmark(url="http://x.com?a=1&b=2", title="T & < > ' \""))
    e = Exporter(m)
    content = e.export_to_content("xml")
    # XML escape
    assert "&amp;" in content
    assert "&lt;" in content
    assert "&gt;" in content
    assert "&apos;" in content
    assert "&quot;" in content


def test_export_to_content_markdown_favorites_marker():
    m = BookmarkManager()
    m.add(Bookmark(url="http://x.com", title="Fav", is_favorite=True))
    m.add(Bookmark(url="http://y.com", title="NoFav", is_favorite=False))
    e = Exporter(m)
    content = e.export_to_content("markdown")
    assert "⭐" in content
    # both titles present
    assert "[Fav](http://x.com)" in content
    assert "[NoFav](http://y.com)" in content


def test_export_to_content_opml_structure():
    m = _make_manager()
    e = Exporter(m)
    content = e.export_to_content("opml")
    assert content.startswith("<?xml version=\"1.0\"")
    assert "<opml version=\"2.0\">" in content
    assert 'type="bookmark"' in content


def test_export_to_content_unknown_format_returns_none():
    e = Exporter()
    assert e.export_to_content("unknown") is None


def test_export_to_file_auto_detect_format():
    m = _make_manager()
    e = Exporter(m)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "out.json"
        result = e.export_to_file(str(path))
        assert result.format == "json"
        assert result.total_exported == 3
        assert os.path.exists(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 3


def test_export_to_file_unsupported_extension():
    e = Exporter()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "out.xyz"
        result = e.export_to_file(str(path))
        assert result.errors
        assert "Unsupported format" in result.errors[0]


def test_export_filtered_category():
    m = BookmarkManager()
    m.add(Bookmark(url="http://a.com", title="A", category="tech"))
    m.add(Bookmark(url="http://b.com", title="B", category="news"))
    e = Exporter(m)
    content = e.export_filtered("json", category="tech")
    data = json.loads(content)
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_export_filtered_tag():
    m = BookmarkManager()
    m.add(Bookmark(url="http://a.com", title="A", tags=["python"]))
    m.add(Bookmark(url="http://b.com", title="B", tags=["news"]))
    e = Exporter(m)
    content = e.export_filtered("json", tag="python")
    data = json.loads(content)
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_export_filtered_favorites_only():
    m = BookmarkManager()
    m.add(Bookmark(url="http://a.com", title="A", is_favorite=True))
    m.add(Bookmark(url="http://b.com", title="B", is_favorite=False))
    e = Exporter(m)
    content = e.export_filtered("json", favorites_only=True)
    data = json.loads(content)
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_export_idempotence():
    m = _make_manager()
    e = Exporter(m)
    c1 = e.export_to_content("json")
    c2 = e.export_to_content("json")
    assert c1 == c2


def test_export_unicode_roundtrip():
    m = BookmarkManager()
    m.add(Bookmark(url="http://x.com", title="Привет мир 🌍", description="Тест"))
    e = Exporter(m)
    content = e.export_to_content("json")
    data = json.loads(content)
    assert data[0]["title"] == "Привет мир 🌍"
    assert data[0]["description"] == "Тест"


def test_export_empty_manager_all_formats():
    e = Exporter(BookmarkManager())
    for fmt in ["json", "csv", "html", "xml", "markdown", "opml"]:
        content = e.export_to_content(fmt)
        assert content is not None
        assert len(content) > 0
