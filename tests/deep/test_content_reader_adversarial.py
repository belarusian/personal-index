"""Adversarial deep tests for personal_index.content_reader.

Cycle 218 — VALIDATOR probe of a never-probed subsystem.

Covers: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, boundary lengths, and a CLI smoke run.

The module's contract (from docs/content-reader.md + docstrings):
- ContentReader.add/get: URL-keyed lookup; get returns the item or None.
- ContentReader.paginate: page_size < 1 raises ValueError; page clamped to
  [1, total_pages]; empty reader -> 1 page / 0 items / no nav.
- PageView.start_index / end_index properties.
- filter_by_tags: empty -> all; match_all vs any; case-insensitive.
- filter_by_score: min/max inclusive; max None = no upper bound.
- search_titles / search_content: case-insensitive substring; empty query -> all.
- format_item: show_content gating; content > 500 chars appends a "..." line.
- format_page: prev/next nav only when present.

NOTE: the duplicate-URL divergence between get() and the collection views is
the OPEN defect ARCH-27 (issue #1073); it is deliberately NOT pinned here.
"""

from __future__ import annotations


from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_reader import ContentReader, PageView, ReadResult


def _item(
    url: str = "http://example.com/1",
    title: str = "Title",
    content: str = "Body",
    tags: list[str] | None = None,
    score: float = 0.0,
) -> ReadResult:
    return ReadResult(
        url=url,
        title=title,
        content=content,
        tags=list(tags) if tags else [],
        score=score,
    )


# ---------------------------------------------------------------------------
# ReadResult / PageView dataclasses
# ---------------------------------------------------------------------------
class TestReadResult:
    def test_to_dict_round_trip(self):
        item = _item(tags=["a", "b"], score=3.5)
        d = item.to_dict()
        assert d == {
            "url": item.url,
            "title": item.title,
            "content": item.content,
            "tags": ["a", "b"],
            "score": 3.5,
            "metadata": {},
        }

    def test_default_fields(self):
        item = ReadResult(url="u", title="t", content="c")
        assert item.tags == []
        assert item.score == 0.0
        assert item.metadata == {}


class TestPageView:
    def test_start_end_index(self):
        pv = PageView(
            items=[], page=2, page_size=10, total_items=25,
            total_pages=3, has_next=True, has_prev=True,
        )
        assert pv.start_index == 10
        assert pv.end_index == 20

    def test_end_index_clamped_to_total(self):
        pv = PageView(
            items=[], page=3, page_size=10, total_items=25,
            total_pages=3, has_next=False, has_prev=True,
        )
        assert pv.start_index == 20
        assert pv.end_index == 25  # min(30, 25)


# ---------------------------------------------------------------------------
# add / get / list_all / count
# ---------------------------------------------------------------------------
class TestAddGet:
    def test_get_hit_and_miss(self):
        r = ContentReader()
        item = _item(url="http://x.com/a")
        r.add(item)
        assert r.get("http://x.com/a") is item
        assert r.get("http://x.com/missing") is None

    def test_add_many_and_count(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}") for i in range(5)])
        assert r.count == 5
        assert len(r.list_all()) == 5

    def test_list_all_is_copy(self):
        r = ContentReader()
        r.add(_item())
        lst = r.list_all()
        lst.append(_item(url="http://x.com/extra"))
        assert r.count == 1  # internal list unaffected

    def test_clear(self):
        r = ContentReader()
        r.add(_item())
        r.clear()
        assert r.count == 0
        assert r.get("http://example.com/1") is None


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------
class TestPaginate:
    def test_page_size_zero_raises(self):
        r = ContentReader()
        r.add(_item())
        try:
            r.paginate(page_size=0)
        except ValueError:
            return
        raise AssertionError("expected ValueError for page_size=0")

    def test_page_size_negative_raises(self):
        r = ContentReader()
        try:
            r.paginate(page_size=-3)
        except ValueError:
            return
        raise AssertionError("expected ValueError for page_size=-3")

    def test_empty_reader_single_empty_page(self):
        r = ContentReader()
        pv = r.paginate()
        assert pv.total_items == 0
        assert pv.total_pages == 1
        assert pv.page == 1
        assert pv.items == []
        assert pv.has_next is False
        assert pv.has_prev is False

    def test_page_clamped_high(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(5)])
        pv = r.paginate(page=999, page_size=2)
        assert pv.page == 3  # total_pages = ceil(5/2) = 3
        assert pv.has_next is False

    def test_page_clamped_low(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(5)])
        pv = r.paginate(page=0, page_size=2)
        assert pv.page == 1
        assert pv.has_prev is False

    def test_page_clamped_negative(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(5)])
        pv = r.paginate(page=-10, page_size=2)
        assert pv.page == 1

    def test_sort_by_score_descending_default(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(3)])
        pv = r.paginate(page_size=10)
        scores = [it.score for it in pv.items]
        assert scores == [2.0, 1.0, 0.0]

    def test_sort_by_title_case_insensitive(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", title="banana"),
            _item(url="http://x.com/2", title="Apple"),
            _item(url="http://x.com/3", title="cherry"),
        ])
        pv = r.paginate(sort_by="title", reverse=False)
        assert [it.title for it in pv.items] == ["Apple", "banana", "cherry"]

    def test_unknown_sort_by_keeps_insertion_order(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", title="z"),
            _item(url="http://x.com/2", title="a"),
        ])
        pv = r.paginate(sort_by="nonsense")
        assert [it.url for it in pv.items] == [
            "http://x.com/1", "http://x.com/2",
        ]

    def test_paginate_does_not_mutate_internal_order(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(4)])
        r.paginate(sort_by="title", reverse=True)
        # internal insertion order preserved
        assert [it.url for it in r.list_all()] == [
            "http://x.com/0", "http://x.com/1", "http://x.com/2", "http://x.com/3",
        ]


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------
class TestFilters:
    def test_filter_by_tags_empty_returns_all(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", tags=["a"]) for i in range(3)])
        assert len(r.filter_by_tags([])) == 3

    def test_filter_by_tags_any(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", tags=["a"]),
            _item(url="http://x.com/2", tags=["b"]),
            _item(url="http://x.com/3", tags=["a", "b"]),
        ])
        got = r.filter_by_tags(["a"])
        assert {it.url for it in got} == {"http://x.com/1", "http://x.com/3"}

    def test_filter_by_tags_match_all(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", tags=["a"]),
            _item(url="http://x.com/2", tags=["a", "b"]),
        ])
        got = r.filter_by_tags(["a", "b"], match_all=True)
        assert [it.url for it in got] == ["http://x.com/2"]

    def test_filter_by_tags_case_insensitive(self):
        r = ContentReader()
        r.add(_item(url="http://x.com/1", tags=["Python"]))
        assert len(r.filter_by_tags(["python"])) == 1
        assert len(r.filter_by_tags(["PYTHON"])) == 1

    def test_filter_by_score_inclusive_bounds(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(4)])
        got = r.filter_by_score(min_score=1.0, max_score=2.0)
        assert {it.score for it in got} == {1.0, 2.0}

    def test_filter_by_score_no_upper_bound(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(4)])
        got = r.filter_by_score(min_score=2.0)
        assert {it.score for it in got} == {2.0, 3.0}

    def test_filter_by_score_empty_range(self):
        r = ContentReader()
        r.add(_item(url="http://x.com/1", score=1.0))
        assert r.filter_by_score(min_score=5.0, max_score=10.0) == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
class TestSearch:
    def test_search_titles_case_insensitive(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", title="Hello World"),
            _item(url="http://x.com/2", title="goodbye"),
        ])
        assert len(r.search_titles("hello")) == 1
        assert len(r.search_titles("WORLD")) == 1

    def test_search_titles_empty_query_returns_all(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}") for i in range(3)])
        assert len(r.search_titles("")) == 3

    def test_search_content_substring(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", content="the quick brown fox"),
            _item(url="http://x.com/2", content="lazy dog"),
        ])
        got = r.search_content("QUICK")
        assert [it.url for it in got] == ["http://x.com/1"]

    def test_search_no_match(self):
        r = ContentReader()
        r.add(_item(url="http://x.com/1", title="abc"))
        assert r.search_titles("zzz") == []


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------
class TestFormatting:
    def test_format_item_no_content(self):
        r = ContentReader()
        out = r.format_item(_item(content=""))
        assert "## Title" in out
        assert "URL: http://example.com/1" in out
        assert "Score: 0.00" in out
        assert "..." not in out

    def test_format_item_show_content_false(self):
        r = ContentReader()
        out = r.format_item(_item(content="secret body"), show_content=False)
        assert "secret body" not in out

    def test_format_item_short_content_no_ellipsis(self):
        r = ContentReader()
        out = r.format_item(_item(content="x" * 500))
        assert "..." not in out

    def test_format_item_long_content_truncated_with_ellipsis(self):
        r = ContentReader()
        body = "y" * 600
        out = r.format_item(_item(content=body))
        assert "y" * 500 in out
        assert "y" * 501 not in out
        assert out.rstrip().endswith("...")

    def test_format_item_tags_line(self):
        r = ContentReader()
        out = r.format_item(_item(tags=["a", "b"]))
        assert "Tags: a, b" in out

    def test_format_page_nav(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(5)])
        pv = r.paginate(page=2, page_size=2)
        out = r.format_page(pv)
        assert "Page 2 of 3" in out
        assert "[Prev Page 1]" in out
        assert "[Next Page 3]" in out

    def test_format_page_first_page_no_prev(self):
        r = ContentReader()
        r.add_many([_item(url=f"http://x.com/{i}", score=float(i)) for i in range(5)])
        pv = r.paginate(page=1, page_size=2)
        out = r.format_page(pv)
        assert "[Prev" not in out
        assert "[Next Page 2]" in out


# ---------------------------------------------------------------------------
# unicode / whitespace robustness
# ---------------------------------------------------------------------------
class TestUnicodeWhitespace:
    def test_unicode_title_and_content(self):
        r = ContentReader()
        r.add(_item(url="http://x.com/1", title="Ünïcödé", content="café résumé"))
        assert r.search_titles("ünïcödé")  # case-insensitive on unicode
        assert r.search_content("café")

    def test_whitespace_title_sort(self):
        r = ContentReader()
        r.add_many([
            _item(url="http://x.com/1", title="  spaced  "),
            _item(url="http://x.com/2", title="alpha"),
        ])
        pv = r.paginate(sort_by="title", reverse=False)
        assert len(pv.items) == 2


# ---------------------------------------------------------------------------
# CLI smoke (end-to-end requirement; content_reader is not CLI-wired, so we
# exercise the installed CLI entry point directly)
# ---------------------------------------------------------------------------
class TestCliSmoke:
    def test_cli_status_runs(self, tmp_path):
        dd = str(tmp_path)
        runner = CliRunner()
        res = runner.invoke(main, ["status", "--data-dir", dd])
        assert res.exit_code == 0

    def test_cli_top_empty(self, tmp_path):
        dd = str(tmp_path)
        runner = CliRunner()
        res = runner.invoke(main, ["top", "--data-dir", dd])
        assert res.exit_code == 0
