"""Adversarial deep tests for personal_index.pagination.

Contract source: personal_index/pagination.py docstrings for PageParams
(offset/limit + __post_init__ clamping), PageResult (total_pages guard path,
has_next/has_prev/next_page/prev_page, start_index/end_index, to_dict) and
Paginator (get_page slicing, total_items/total_pages, iterate_pages). These
tests pin the documented behavior against adversarial inputs: out-of-range /
zero / negative page and per_page values, empty and single-item collections,
unicode + duplicate items, exact page boundaries, to_dict round-trip,
property idempotence (pure getters), and one end-to-end CLI run (init +
search on an empty index).
"""

from __future__ import annotations

import math

from personal_index.pagination import PageParams, PageResult, Paginator


# --- PageParams clamping + offset/limit ------------------------------------

def test_page_params_defaults():
    p = PageParams()
    assert p.page == 1
    assert p.per_page == 20
    assert p.max_per_page == 100
    assert p.offset == 0
    assert p.limit == 20


def test_page_params_clamps_page_below_one():
    assert PageParams(page=0).page == 1
    assert PageParams(page=-5).page == 1
    assert PageParams(page=1).page == 1


def test_page_params_clamps_per_page_to_range():
    # per_page below 1 -> 1
    assert PageParams(per_page=0).per_page == 1
    assert PageParams(per_page=-10).per_page == 1
    # per_page above max_per_page -> max_per_page
    assert PageParams(per_page=500).per_page == 100
    assert PageParams(per_page=100).per_page == 100
    # in-range stays
    assert PageParams(per_page=25).per_page == 25


def test_page_params_custom_max_per_page():
    assert PageParams(per_page=50, max_per_page=30).per_page == 30
    # max_per_page below 1 collapses per_page to 1 (max(1, min(per, max)))
    assert PageParams(per_page=20, max_per_page=0).per_page == 1
    assert PageParams(per_page=20, max_per_page=-5).per_page == 1


def test_page_params_offset_and_limit_consistent():
    p = PageParams(page=3, per_page=10)
    assert p.offset == 20
    assert p.limit == 10
    p2 = PageParams(page=1, per_page=1)
    assert p2.offset == 0
    assert p2.limit == 1


# --- PageResult.total_pages guard path -------------------------------------

def test_total_pages_guard_empty_returns_one():
    assert PageResult([], 0, 1, 20).total_pages == 1
    assert PageResult([], 0, 1, 1).total_pages == 1


def test_total_pages_exact_boundaries():
    # total == per_page -> exactly 1 page (not 2)
    assert PageResult([], 20, 1, 20).total_pages == 1
    # total == per_page + 1 -> 2 pages
    assert PageResult([], 21, 1, 20).total_pages == 2
    # total == 2*per_page -> 2 pages
    assert PageResult([], 40, 1, 20).total_pages == 2
    # total == 2*per_page + 1 -> 3 pages
    assert PageResult([], 41, 1, 20).total_pages == 3
    # total == 1 -> 1 page
    assert PageResult([], 1, 1, 20).total_pages == 1
    # total == 100, per_page == 20 -> 5
    assert PageResult([], 100, 1, 20).total_pages == 5


def test_total_pages_matches_ceil_formula():
    for total in range(0, 250):
        for per_page in (1, 7, 20, 100):
            expected = max(1, math.ceil(total / per_page))
            got = PageResult([], total, 1, per_page).total_pages
            assert got == expected, (total, per_page, got, expected)


# --- PageResult navigation properties --------------------------------------

def test_has_next_has_prev_at_boundaries():
    # single page: no next, no prev
    r = PageResult([], 10, 1, 20)
    assert r.has_next is False
    assert r.has_prev is False
    assert r.next_page is None
    assert r.prev_page is None


def test_middle_page_navigation():
    r = PageResult([], 100, 2, 20)  # 5 pages total
    assert r.total_pages == 5
    assert r.has_next is True
    assert r.has_prev is True
    assert r.next_page == 3
    assert r.prev_page == 1


def test_last_page_no_next():
    r = PageResult([], 100, 5, 20)
    assert r.has_next is False
    assert r.next_page is None
    assert r.has_prev is True
    assert r.prev_page == 4


def test_first_page_no_prev():
    r = PageResult([], 100, 1, 20)
    assert r.has_prev is False
    assert r.prev_page is None
    assert r.has_next is True
    assert r.next_page == 2


# --- PageResult start_index / end_index ------------------------------------

def test_start_end_index_first_page():
    r = PageResult(list(range(5)), 5, 1, 20)
    assert r.start_index == 1
    assert r.end_index == 5  # min(1*20, 5)


def test_start_end_index_middle_full_page():
    r = PageResult(list(range(20)), 100, 2, 20)
    assert r.start_index == 21
    assert r.end_index == 40  # min(2*20, 100)


def test_start_end_index_last_partial_page():
    r = PageResult(list(range(1)), 41, 3, 20)
    assert r.start_index == 41
    assert r.end_index == 41  # min(3*20, 41)


def test_start_end_index_empty():
    r = PageResult([], 0, 1, 20)
    assert r.start_index == 1
    assert r.end_index == 0  # min(20, 0)


# --- PageResult.to_dict round-trip -----------------------------------------

def test_to_dict_contains_all_documented_keys():
    r = PageResult(["a", "b"], 2, 1, 20)
    d = r.to_dict()
    assert set(d) == {
        "items", "total", "page", "per_page", "total_pages",
        "has_next", "has_prev", "next_page", "prev_page",
        "start_index", "end_index",
    }
    assert d["items"] == ["a", "b"]
    assert d["total"] == 2
    assert d["total_pages"] == 1
    assert d["has_next"] is False
    assert d["prev_page"] is None


def test_to_dict_round_trip_reconstructs_equal_result():
    r = PageResult(["x", "y", "z"], 41, 2, 20)
    d = r.to_dict()
    r2 = PageResult(d["items"], d["total"], d["page"], d["per_page"])
    assert r2.to_dict() == d
    assert r2.total_pages == r.total_pages
    assert r2.has_next == r.has_next
    assert r2.start_index == r.start_index
    assert r2.end_index == r.end_index


# --- Paginator.get_page slicing --------------------------------------------

def test_paginator_get_page_first():
    items = list(range(50))
    p = Paginator(items, per_page=20)
    r = p.get_page(1)
    assert r.items == list(range(0, 20))
    assert r.total == 50
    assert r.page == 1
    assert r.per_page == 20


def test_paginator_get_page_last_partial():
    items = list(range(41))
    p = Paginator(items, per_page=20)
    r = p.get_page(3)
    assert r.items == list(range(40, 41))
    assert len(r.items) == 1


def test_paginator_get_page_out_of_range_returns_empty():
    items = list(range(10))
    p = Paginator(items, per_page=20)
    r = p.get_page(99)
    assert r.items == []
    assert r.total == 10


def test_paginator_get_page_clamps_page_below_one():
    items = list(range(10))
    p = Paginator(items, per_page=20)
    r = p.get_page(0)
    assert r.page == 1
    assert r.items == list(range(10))


def test_paginator_get_page_per_page_override():
    items = list(range(10))
    p = Paginator(items, per_page=20)
    r = p.get_page(1, per_page=3)
    assert r.per_page == 3
    assert r.items == [0, 1, 2]
    assert r.total_pages == 4  # ceil(10/3)


def test_paginator_get_page_per_page_override_clamped_to_max():
    items = list(range(10))
    p = Paginator(items, per_page=20, max_per_page=5)
    r = p.get_page(1, per_page=500)
    assert r.per_page == 5
    assert r.items == [0, 1, 2, 3, 4]


def test_paginator_get_page_per_page_zero_clamped_to_one():
    items = list(range(10))
    p = Paginator(items, per_page=20)
    r = p.get_page(1, per_page=0)
    assert r.per_page == 1
    assert r.items == [0]


# --- Paginator.total_items / total_pages -----------------------------------

def test_paginator_total_items_and_pages():
    p = Paginator(list(range(41)), per_page=20)
    assert p.total_items == 41
    assert p.total_pages == 3


def test_paginator_total_pages_empty_is_one():
    p = Paginator([], per_page=20)
    assert p.total_items == 0
    assert p.total_pages == 1


def test_paginator_total_pages_exact_multiple():
    p = Paginator(list(range(40)), per_page=20)
    assert p.total_pages == 2


# --- Paginator.iterate_pages -----------------------------------------------

def test_iterate_pages_empty_returns_single_empty_page():
    p = Paginator([], per_page=20)
    pages = p.iterate_pages()
    assert len(pages) == 1
    assert pages[0].items == []
    assert pages[0].total == 0


def test_iterate_pages_full_coverage_no_overlap():
    items = list(range(41))
    p = Paginator(items, per_page=20)
    pages = p.iterate_pages()
    assert len(pages) == 3
    # concatenating all pages reproduces the original order exactly
    flat = [x for pg in pages for x in pg.items]
    assert flat == items
    # page numbers are 1..N in order
    assert [pg.page for pg in pages] == [1, 2, 3]


def test_iterate_pages_per_page_override():
    items = list(range(10))
    p = Paginator(items, per_page=20)
    pages = p.iterate_pages(per_page=3)
    assert len(pages) == 4  # ceil(10/3)
    assert [pg.per_page for pg in pages] == [3, 3, 3, 3]
    flat = [x for pg in pages for x in pg.items]
    assert flat == items


def test_iterate_pages_idempotent():
    items = list(range(25))
    p = Paginator(items, per_page=10)
    a = p.iterate_pages()
    b = p.iterate_pages()
    assert [pg.to_dict() for pg in a] == [pg.to_dict() for pg in b]


# --- adversarial item payloads (unicode / duplicate / empty strings) -------

def test_paginator_with_unicode_and_duplicate_items():
    items = ["héllo", "héllo", "世界", "", "   ", "héllo"]
    p = Paginator(items, per_page=2)
    pages = p.iterate_pages()
    flat = [x for pg in pages for x in pg.items]
    assert flat == items
    assert len(pages) == 3  # ceil(6/2)


def test_page_result_items_passthrough_not_mutated():
    items = ["a", "b", "c"]
    r = PageResult(items, 3, 1, 20)
    # to_dict must not mutate the underlying items list
    r.to_dict()
    assert items == ["a", "b", "c"]
    assert r.items is items


# --- property idempotence (pure getters) -----------------------------------

def test_properties_are_pure_and_stable():
    r = PageResult(list(range(5)), 41, 2, 20)
    first = {
        "total_pages": r.total_pages,
        "has_next": r.has_next,
        "has_prev": r.has_prev,
        "next_page": r.next_page,
        "prev_page": r.prev_page,
        "start_index": r.start_index,
        "end_index": r.end_index,
    }
    for _ in range(3):
        again = {
            "total_pages": r.total_pages,
            "has_next": r.has_next,
            "has_prev": r.has_prev,
            "next_page": r.next_page,
            "prev_page": r.prev_page,
            "start_index": r.start_index,
            "end_index": r.end_index,
        }
        assert again == first


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_search_empty_index(tmp_path):
    """End-to-end: init + search on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["search", "python", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    # empty index -> the documented "No indexed content found" notice
    assert "No indexed content found" in r.output
