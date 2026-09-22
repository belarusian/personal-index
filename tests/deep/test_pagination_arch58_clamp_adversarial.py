"""Adversarial deep tests for personal_index.pagination - ARCH-58 clamp + reworded docstring contracts.

Complements test_pagination_adversarial.py (last touched 09-07) which predates:
  * ARCH-58 (09-13): clamp Paginator per_page in __init__ so total_pages /
    get_page / iterate_pages all operate on the SAME effective page size.
  * six PageResult docstring rewords (09-13): total_pages / has_next /
    has_prev / next_page / prev_page / start_index / end_index now state
    explicit guard paths + preconditions (per_page != 0 for the pure
    property; clamping is the Paginator's job, not the dataclass's).

These pins attack the NEW contracts with adversarial inputs: constructor
per_page of 0 / negative / over-max (clamp consistency across all three
entry points), PageParams max_per_page=0, a hand-built PageResult with
per_page=0 (documented ZeroDivisionError precondition), get_page /
iterate_pages per_page overrides of 0 / negative / over-max, the reworded
guard paths (start_index page-1 == 1, end_index clamp to total, next/prev
None at boundaries), to_dict on an empty result, and one end-to-end run
through the installed CLI entry point.

All assertions re-derived against the ACTUAL result shape on current main
(cycle 353), not the defect-era shape.
"""

from __future__ import annotations

import pytest

from personal_index.pagination import PageParams, PageResult, Paginator


# --- ARCH-58: constructor per_page clamp consistency -----------------------
# The constructor clamps per_page to max(1, min(per_page, max_per_page)).
# total_pages, get_page and iterate_pages must ALL agree on that effective
# size - a one-sided clamp (e.g. only get_page) would leak a partial page.


def test_ctor_per_page_zero_clamped_to_one_consistent():
    p = Paginator(list(range(10)), per_page=0)
    assert p._per_page == 1
    assert p.total_pages == 10  # ceil(10/1)
    assert p.get_page(1).per_page == 1
    assert p.get_page(1).items == [0]
    pages = p.iterate_pages()
    assert len(pages) == 10
    assert [pg.per_page for pg in pages] == [1] * 10
    # full coverage, no overlap
    assert [x for pg in pages for x in pg.items] == list(range(10))


def test_ctor_per_page_negative_clamped_to_one():
    p = Paginator(list(range(10)), per_page=-5)
    assert p._per_page == 1
    assert p.total_pages == 10
    assert p.get_page(1).items == [0]


def test_ctor_per_page_over_max_clamped_to_max():
    p = Paginator(list(range(10)), per_page=500, max_per_page=5)
    assert p._per_page == 5
    assert p.total_pages == 2  # ceil(10/5)
    assert p.get_page(1).items == [0, 1, 2, 3, 4]
    assert p.get_page(2).items == [5, 6, 7, 8, 9]


def test_ctor_per_page_clamp_consistent_across_all_entry_points():
    # the load-bearing ARCH-58 invariant: one effective size everywhere
    for pp in (0, -3, 1, 5, 500):
        p = Paginator(list(range(10)), per_page=pp, max_per_page=5)
        eff = p._per_page
        assert p.total_pages == max(1, -(-10 // eff))  # ceil(10/eff)
        assert p.get_page(1).per_page == eff
        pages = p.iterate_pages()
        assert all(pg.per_page == eff for pg in pages)
        assert [x for pg in pages for x in pg.items] == list(range(10))


# --- PageParams max_per_page edge ------------------------------------------


def test_page_params_max_per_page_zero_clamps_to_one():
    pp = PageParams(page=1, per_page=20, max_per_page=0)
    # max(1, min(20, 0)) == max(1, 0) == 1
    assert pp.per_page == 1
    assert pp.offset == 0
    assert pp.limit == 1


def test_page_params_per_page_negative_clamps_to_one():
    pp = PageParams(page=1, per_page=-10, max_per_page=100)
    assert pp.per_page == 1


# --- hand-built PageResult per_page=0 -> documented ZeroDivisionError ------
# The docstring states: "a PageResult constructed directly with per_page=0
# raises ZeroDivisionError here (the Paginator never produces such a
# result, as it clamps via PageParams)." Pin that precondition.


def test_hand_built_page_result_per_page_zero_raises():
    with pytest.raises(ZeroDivisionError):
        PageResult([], 0, 1, 0).total_pages


def test_hand_built_page_result_per_page_zero_has_next_raises():
    # has_next reads total_pages -> same ZeroDivisionError precondition
    with pytest.raises(ZeroDivisionError):
        PageResult([], 0, 1, 0).has_next


# --- get_page / iterate_pages per_page override of 0 / negative / over-max --


def test_get_page_per_page_negative_clamped_to_one():
    p = Paginator(list(range(10)), per_page=20)
    r = p.get_page(1, per_page=-3)
    assert r.per_page == 1
    assert r.items == [0]


def test_get_page_per_page_over_max_clamped_to_max():
    p = Paginator(list(range(10)), per_page=20, max_per_page=5)
    r = p.get_page(1, per_page=500)
    assert r.per_page == 5
    assert r.items == [0, 1, 2, 3, 4]


def test_iterate_pages_per_page_zero_clamped_to_one():
    p = Paginator(list(range(10)), per_page=20)
    pages = p.iterate_pages(per_page=0)
    assert len(pages) == 10
    assert [pg.per_page for pg in pages] == [1] * 10
    assert [x for pg in pages for x in pg.items] == list(range(10))


def test_iterate_pages_per_page_over_max_clamped_to_max():
    p = Paginator(list(range(10)), per_page=20, max_per_page=3)
    pages = p.iterate_pages(per_page=500)
    assert [pg.per_page for pg in pages] == [3, 3, 3, 3]
    assert [x for pg in pages for x in pg.items] == list(range(10))


# --- reworded docstring guard paths ----------------------------------------


def test_start_index_page_one_is_one_never_zero():
    # "on page 1 it returns 1 (the first item overall); for page >= 1 it
    # never returns 0 or a negative value"
    r = PageResult(list(range(5)), 5, 1, 20)
    assert r.start_index == 1
    assert r.start_index > 0


def test_end_index_clamped_to_total_on_partial_page():
    # "on the final partial page (page*per_page > total), the value is
    # clamped to total so it never exceeds the number of items that
    # actually exist"
    r = PageResult(list(range(1)), 41, 3, 20)
    assert r.end_index == 41  # min(60, 41)
    assert r.end_index <= r.total


def test_end_index_empty_is_zero():
    r = PageResult([], 0, 1, 20)
    assert r.end_index == 0  # min(20, 0)


def test_next_page_none_on_last_page():
    # "on the final page (page == total_pages) it returns None (never a
    # page number past the last page)"
    r = PageResult(list(range(5)), 41, 3, 20)  # total_pages == 3
    assert r.has_next is False
    assert r.next_page is None


def test_prev_page_none_on_first_page():
    # "on the first page (page == 1) it returns None (never 0 or a
    # negative page number)"
    r = PageResult(list(range(5)), 41, 1, 20)
    assert r.has_prev is False
    assert r.prev_page is None


def test_total_pages_total_less_than_per_page_is_one():
    # "when total == 0 (or total < per_page), returns 1 (never 0)"
    r = PageResult(list(range(5)), 5, 1, 20)
    assert r.total_pages == 1
    assert r.has_next is False
    assert r.next_page is None


# --- to_dict on an empty result --------------------------------------------


def test_to_dict_empty_result_full_key_set():
    r = PageResult([], 0, 1, 20)
    d = r.to_dict()
    assert set(d) == {
        "items", "total", "page", "per_page", "total_pages",
        "has_next", "has_prev", "next_page", "prev_page",
        "start_index", "end_index",
    }
    assert d["items"] == []
    assert d["total"] == 0
    assert d["total_pages"] == 1
    assert d["has_next"] is False
    assert d["has_prev"] is False
    assert d["next_page"] is None
    assert d["prev_page"] is None
    assert d["start_index"] == 1
    assert d["end_index"] == 0


# --- get_page out-of-range / below-one page --------------------------------


def test_get_page_beyond_last_returns_empty_page():
    p = Paginator(list(range(5)), per_page=2)
    r = p.get_page(99)
    assert r.items == []
    assert r.page == 99
    assert r.total_pages == 3
    assert r.has_next is False


def test_get_page_below_one_clamps_to_one():
    p = Paginator(list(range(5)), per_page=2)
    r = p.get_page(0)
    assert r.page == 1
    assert r.items == [0, 1]


# --- end-to-end: installed CLI entry point ---------------------------------


def test_end_to_end_cli_entry_point_runs():
    """pagination is not wired into a dedicated CLI command; exercise the
    installed entry point to confirm the package imports cleanly in-process
    and the CLI still runs green after the probed change."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    r = runner.invoke(main, ["--version"])
    assert r.exit_code == 0, r.output
    assert "version" in r.output.lower()

    r = runner.invoke(main, ["--help"])
    assert r.exit_code == 0, r.output
    assert "COMMAND" in r.output
