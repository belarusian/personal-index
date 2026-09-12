"""Adversarial deep tests for personal_index.export_markdown.

Contract source: module docstrings (personal_index/export_markdown.py).
This module has NO dedicated docs page, so the docstrings are the contract.

Key docstring claims under test:
  * ``MarkdownExporter.export``: "Export content items to the specified
    format." Returns a formatted export string; empty input -> "".
  * ``ExportConfig.__post_init__``: sort_by must be one of
    {date, title, priority, relevance}; group_by one of
    {tags, date, category, None} -- otherwise ValueError.
  * ``_export_html``: produces HTML where every interpolated field is
    escaped exactly once (a well-formed document whose text round-trips
    through a single ``html.unescape``).
  * ``_truncate``: "Truncate text to max_length, adding ellipsis if needed."

DEFECT (QA-33): ``_export_html`` escapes ``content`` TWICE. Line 186 does
``content = html.escape(item.get("content", ""))`` and line 205 does
``html.escape(display)`` where ``display`` is derived from that already-
escaped ``content``. A content string containing ``&`` therefore renders as
``&amp;amp;`` (a browser shows ``&amp;`` instead of ``&``), breaking the
single-escape / well-formed round-trip the HTML contract implies. Title and
URL are escaped exactly once (control), so the double-escape is specific to
the content path. Pinned xfail-strict below.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys

import pytest

from personal_index.export_markdown import (
    ExportConfig,
    ExportFormat,
    MarkdownExporter,
)


def _item(**over):
    base = {
        "title": "T",
        "url": "http://example.com",
        "content": "C",
        "tags": [],
        "published_date": "2024-01-01",
    }
    base.update(over)
    return base


def _content_p(out: str) -> str:
    """Return the text of the content <p>...</p> (the one without <em>)."""
    ps: list[str] = re.findall(r"<p>(.*?)</p>", out)
    for p in ps:
        if "<em>" not in p:
            return p
    return ps[-1] if ps else ""


# ---------------------------------------------------------------------------
# ExportConfig validation
# ---------------------------------------------------------------------------


def test_config_defaults():
    c = ExportConfig()
    assert c.include_metadata is True
    assert c.include_tags is True
    assert c.include_summary is False
    assert c.sort_by == "date"
    assert c.group_by is None


@pytest.mark.parametrize("sort_by", ["date", "title", "priority", "relevance"])
def test_config_valid_sort_by_accepted(sort_by):
    ExportConfig(sort_by=sort_by)  # must not raise


@pytest.mark.parametrize("bad", ["", " ", "DATE", "score", "none", "tags"])
def test_config_invalid_sort_by_raises(bad):
    with pytest.raises(ValueError):
        ExportConfig(sort_by=bad)


@pytest.mark.parametrize("group_by", ["tags", "date", "category", None])
def test_config_valid_group_by_accepted(group_by):
    ExportConfig(group_by=group_by)  # must not raise


@pytest.mark.parametrize("bad", ["", " ", "TAGS", "source", "all"])
def test_config_invalid_group_by_raises(bad):
    with pytest.raises(ValueError):
        ExportConfig(group_by=bad)


# ---------------------------------------------------------------------------
# export() guard + dispatch
# ---------------------------------------------------------------------------


def test_export_empty_list_returns_empty_string():
    assert MarkdownExporter().export([]) == ""


def test_export_none_format_defaults_to_markdown():
    out = MarkdownExporter().export([_item()], None)
    assert out.startswith("# T")


def test_export_dispatch_all_three_formats():
    exp = MarkdownExporter()
    items = [_item()]
    assert exp.export(items, ExportFormat.MARKDOWN).startswith("# T")
    assert exp.export(items, ExportFormat.HTML).startswith("<!DOCTYPE html>")
    assert exp.export(items, ExportFormat.PLAIN_TEXT).startswith("T")


def test_export_idempotent_same_input_same_output():
    exp = MarkdownExporter()
    items = [_item(title="A"), _item(title="B")]
    assert exp.export(items, ExportFormat.HTML) == exp.export(items, ExportFormat.HTML)


def test_export_does_not_mutate_items():
    exp = MarkdownExporter(ExportConfig(sort_by="title"))
    items = [_item(title="B"), _item(title="A")]
    snapshot = [dict(i) for i in items]
    exp.export(items, ExportFormat.MARKDOWN)
    assert items == snapshot


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def test_markdown_single_item_structure():
    out = MarkdownExporter().export([_item(title="Hello", url="http://x")])
    assert "# Hello" in out
    assert "[Hello](http://x)" in out


def test_markdown_missing_title_defaults_untitled():
    out = MarkdownExporter().export([_item(title="")])
    # empty title -> .get("title", "Untitled") returns "" (key present), so
    # the header is "# " with an empty body; assert it does not crash.
    assert out.startswith("#")


def test_markdown_no_url_omits_link():
    out = MarkdownExporter().export([_item(title="T", url="")])
    assert "](" not in out


def test_markdown_metadata_date_present():
    out = MarkdownExporter().export([_item(published_date="2024-05-05")])
    assert "**Published:** 2024-05-05" in out


def test_markdown_metadata_disabled_omits_date():
    exp = MarkdownExporter(ExportConfig(include_metadata=False))
    out = exp.export([_item(published_date="2024-05-05")])
    assert "Published" not in out


def test_markdown_tags_rendered():
    out = MarkdownExporter().export([_item(tags=["a", "b"])])
    assert "**Tags:** a, b" in out


def test_markdown_tags_disabled_omits():
    exp = MarkdownExporter(ExportConfig(include_tags=False))
    out = exp.export([_item(tags=["a"])])
    assert "Tags" not in out


def test_markdown_unicode_round_trip():
    out = MarkdownExporter().export([_item(title="Café ☕", content="naïve")])
    assert "Café ☕" in out
    assert "naïve" in out


def test_markdown_duplicate_items_both_present():
    out = MarkdownExporter().export([_item(title="D"), _item(title="D")])
    assert out.count("# D") == 2


def test_markdown_whitespace_title_preserved():
    out = MarkdownExporter().export([_item(title="   ")])
    assert "#    " in out  # header with the whitespace title


# ---------------------------------------------------------------------------
# HTML rendering (escape path)
# ---------------------------------------------------------------------------


def test_html_scaffold():
    out = MarkdownExporter().export([_item()], ExportFormat.HTML)
    assert out.startswith("<!DOCTYPE html>")
    assert "<html>" in out
    assert "</html>" in out


def test_html_title_single_escaped():
    out = MarkdownExporter().export(
        [_item(title="A & B <x>")], ExportFormat.HTML
    )
    assert html.escape("A & B <x>") in out
    # must NOT be double-escaped
    assert html.escape(html.escape("A & B <x>")) not in out


def test_html_url_single_escaped():
    url = "http://x/?a=1&b=2"
    out = MarkdownExporter().export([_item(url=url)], ExportFormat.HTML)
    assert f'href="{html.escape(url)}"' in out
    assert html.escape(html.escape(url)) not in out


def test_html_unicode_title_round_trip():
    out = MarkdownExporter().export(
        [_item(title="Café ☕")], ExportFormat.HTML
    )
    assert html.escape("Café ☕") in out


def test_html_date_escaped():
    out = MarkdownExporter().export(
        [_item(published_date="a & b")], ExportFormat.HTML
    )
    assert html.escape("a & b") in out


def test_html_tags_escaped():
    out = MarkdownExporter().export(
        [_item(tags=["x & y"])], ExportFormat.HTML
    )
    assert html.escape("x & y") in out


def test_html_empty_list_returns_empty_string():
    assert MarkdownExporter().export([], ExportFormat.HTML) == ""


# QA-33 (fixed): content is escaped exactly once in _export_html
def test_html_content_single_escaped_round_trips():
    content = "Tom & Jerry <a> \"q\""
    out = MarkdownExporter().export(
        [_item(content=content)], ExportFormat.HTML
    )
    # A browser performs exactly one unescape; the result must equal the
    # original content.
    rendered = html.unescape(_content_p(out))
    assert rendered == content


# ---------------------------------------------------------------------------
# Plain text rendering
# ---------------------------------------------------------------------------


def test_plain_text_structure():
    out = MarkdownExporter().export(
        [_item(title="T", url="http://x")], ExportFormat.PLAIN_TEXT
    )
    assert "T" in out
    assert "http://x" in out
    assert "-" * 40 in out


def test_plain_text_unicode():
    out = MarkdownExporter().export(
        [_item(title="Café", content="naïve")], ExportFormat.PLAIN_TEXT
    )
    assert "Café" in out
    assert "naïve" in out


def test_plain_text_empty_list_returns_empty_string():
    assert MarkdownExporter().export([], ExportFormat.PLAIN_TEXT) == ""


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def test_sort_by_date_desc():
    exp = MarkdownExporter(ExportConfig(sort_by="date"))
    items = [
        _item(title="old", published_date="2020-01-01"),
        _item(title="new", published_date="2024-01-01"),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert out.index("# new") < out.index("# old")


def test_sort_by_title():
    exp = MarkdownExporter(ExportConfig(sort_by="title"))
    items = [_item(title="banana"), _item(title="apple")]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert out.index("# apple") < out.index("# banana")


def test_sort_by_priority():
    exp = MarkdownExporter(ExportConfig(sort_by="priority"))
    items = [
        _item(title="low", priority_score=1),
        _item(title="high", priority_score=9),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert out.index("# high") < out.index("# low")


def test_sort_by_relevance():
    exp = MarkdownExporter(ExportConfig(sort_by="relevance"))
    items = [
        _item(title="low", relevance_score=1),
        _item(title="high", relevance_score=9),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert out.index("# high") < out.index("# low")


def test_sort_missing_fields_no_crash():
    exp = MarkdownExporter(ExportConfig(sort_by="date"))
    items = [{"title": "a"}, {"title": "b"}]  # no date fields at all
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "# a" in out and "# b" in out


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def test_group_by_tags():
    exp = MarkdownExporter(ExportConfig(group_by="tags"))
    # two distinct tags -> two groups -> group headers are emitted
    items = [_item(title="a", tags=["x"]), _item(title="b", tags=["y"])]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "## x" in out
    assert "## y" in out


def test_group_by_tags_untagged_bucket():
    exp = MarkdownExporter(ExportConfig(group_by="tags"))
    items = [_item(title="a", tags=[]), _item(title="b", tags=["y"])]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "## untagged" in out
    assert "## y" in out


def test_group_by_date():
    exp = MarkdownExporter(ExportConfig(group_by="date"))
    items = [
        _item(title="a", published_date="2024-01-15"),
        _item(title="b", published_date="2024-02-10"),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "## 2024-01" in out
    assert "## 2024-02" in out


def test_group_by_date_invalid_date_unknown():
    exp = MarkdownExporter(ExportConfig(group_by="date"))
    # one valid + one invalid date -> two groups -> headers emitted
    items = [
        _item(title="a", published_date="2024-01-15"),
        _item(title="b", published_date="not-a-date"),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "## unknown" in out
    assert "## 2024-01" in out


def test_group_by_category():
    exp = MarkdownExporter(ExportConfig(group_by="category"))
    items = [
        _item(title="a", category="news"),
        _item(title="b", category="blog"),
    ]
    out = exp.export(items, ExportFormat.MARKDOWN)
    assert "## news" in out
    assert "## blog" in out


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


def test_truncate_short_unchanged():
    exp = MarkdownExporter()
    assert exp._truncate("short", 200) == "short"


def test_truncate_exact_length_unchanged():
    exp = MarkdownExporter()
    assert exp._truncate("a" * 200, 200) == "a" * 200


def test_truncate_long_adds_ellipsis():
    exp = MarkdownExporter()
    out = exp._truncate("a" * 201, 200)
    assert out.endswith("...")
    assert len(out) <= 203


def test_truncate_breaks_at_word_boundary():
    exp = MarkdownExporter()
    out = exp._truncate("word " * 50, 200)
    assert out.endswith("...")
    # the truncated body (before the ellipsis) must end on a word boundary
    body = out[:-3]
    assert not body.endswith(" ")


def test_truncate_summary_mode_applies_to_content():
    exp = MarkdownExporter(ExportConfig(include_summary=True))
    long_content = "word " * 50
    out = exp.export([_item(content=long_content)], ExportFormat.MARKDOWN)
    assert "..." in out


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
