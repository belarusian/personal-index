"""Tests for pagination utilities."""

from personal_index.pagination import PageParams, PageResult, Paginator


class TestPageParams:
    def test_defaults(self):
        p = PageParams()
        assert p.page == 1
        assert p.per_page == 20
        assert p.offset == 0

    def test_custom_params(self):
        p = PageParams(page=3, per_page=10)
        assert p.offset == 20
        assert p.limit == 10

    def test_page_clamped(self):
        p = PageParams(page=0)
        assert p.page == 1

    def test_per_page_capped(self):
        p = PageParams(per_page=200)
        assert p.per_page == 100


class TestPageResult:
    def test_total_pages(self):
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.total_pages == 5

    def test_page_result_total_pages_pinned(self):
        # normal case: non-integer division, total=25, per_page=10 -> 3
        r = PageResult(items=[], total=25, page=1, per_page=10)
        assert r.total_pages == 3
        # guard case: total=0 -> 1 (never 0)
        g = PageResult(items=[], total=0, page=1, per_page=10)
        assert g.total_pages == 1

    def test_has_next(self):
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.has_next is True
        r2 = PageResult(items=[], total=100, page=5, per_page=20)
        assert r2.has_next is False

    def test_has_next_contract_pinned(self):
        # normal case: page 1 of a multi-page result -> True (1 < 5)
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.has_next is True
        # guard case: final page (page == total_pages) -> False
        g = PageResult(items=[], total=100, page=5, per_page=20)
        assert g.has_next is False
        # guard case: single-page result (total < per_page -> total_pages 1) -> False
        s = PageResult(items=[], total=3, page=1, per_page=20)
        assert s.has_next is False

    def test_has_prev(self):
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.has_prev is False
        r2 = PageResult(items=[], total=100, page=2, per_page=20)
        assert r2.has_prev is True

    def test_has_prev_contract_pinned(self):
        # normal case: page 2 of a multi-page result -> True (2 > 1)
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.has_prev is True
        # guard case: first page (page == 1) -> False (never True on page 1)
        g = PageResult(items=[], total=100, page=1, per_page=20)
        assert g.has_prev is False
        # guard case: later page, per_page 10, page 3 -> True
        s = PageResult(items=[], total=100, page=3, per_page=10)
        assert s.has_prev is True

    def test_next_page_contract_pinned(self):
        # normal case: page 2 of a multi-page result -> 3 (page + 1)
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.next_page == 3
        # guard case: final page (page == total_pages) -> None (never past last)
        g = PageResult(items=[], total=100, page=5, per_page=20)
        assert g.next_page is None
        # guard case: single-page result (page 1 == total_pages) -> None
        s = PageResult(items=[], total=3, page=1, per_page=20)
        assert s.next_page is None

    def test_next_prev_page(self):
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.next_page == 3
        assert r.prev_page == 1

    def test_start_end_index(self):
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.start_index == 21
        assert r.end_index == 40

    def test_end_index_contract_pinned(self):
        # normal case: full page, end_index == page * per_page
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.end_index == 40
        # guard case: final partial page clamps to total
        g = PageResult(items=[], total=25, page=3, per_page=10)
        assert g.end_index == 25
        # guard case: single page with fewer items than per_page
        s = PageResult(items=[], total=3, page=1, per_page=20)
        assert s.end_index == 3

    def test_start_index_contract_pinned(self):
        # normal case: page 2, per_page 20 -> (2-1)*20+1 == 21
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.start_index == 21
        # guard case: page 1 -> 1 (first item overall, never 0)
        g = PageResult(items=[], total=100, page=1, per_page=20)
        assert g.start_index == 1
        # guard case: later page, per_page 10 -> (3-1)*10+1 == 21
        s = PageResult(items=[], total=100, page=3, per_page=10)
        assert s.start_index == 21

    def test_to_dict(self):
        r = PageResult(items=["a"], total=10, page=1, per_page=5)
        d = r.to_dict()
        assert d["total"] == 10
        assert d["total_pages"] == 2


class TestPaginator:
    def test_first_page(self):
        items = list(range(50))
        p = Paginator(items, per_page=10)
        result = p.get_page(1)
        assert len(result.items) == 10
        assert result.items[0] == 0

    def test_last_page(self):
        items = list(range(50))
        p = Paginator(items, per_page=10)
        result = p.get_page(5)
        assert len(result.items) == 10
        assert result.items[0] == 40

    def test_partial_last_page(self):
        items = list(range(55))
        p = Paginator(items, per_page=10)
        result = p.get_page(6)
        assert len(result.items) == 5

    def test_total_items(self):
        items = list(range(100))
        p = Paginator(items)
        assert p.total_items == 100

    def test_total_pages(self):
        items = list(range(95))
        p = Paginator(items, per_page=20)
        assert p.total_pages == 5

    def test_iterate_pages(self):
        items = list(range(25))
        p = Paginator(items, per_page=10)
        pages = p.iterate_pages()
        assert len(pages) == 3
        assert len(pages[0].items) == 10
        assert len(pages[2].items) == 5

    def test_out_of_range_page(self):
        items = list(range(10))
        p = Paginator(items, per_page=5)
        result = p.get_page(100)
        assert len(result.items) == 0

    def test_single_item(self):
        items = ["only"]
        p = Paginator(items)
        result = p.get_page(1)
        assert len(result.items) == 1
        assert result.total_pages == 1

    def test_per_page_zero_clamped_to_one(self):
        # Guard path: explicit per_page=0 must be clamped to 1 by PageParams,
        # not silently coerced to the constructor default.
        items = list(range(50))
        p = Paginator(items, per_page=20)
        result = p.get_page(1, per_page=0)
        assert result.per_page == 1
        assert len(result.items) == 1
        assert result.items[0] == 0

    def test_per_page_normal(self):
        # Normal case: a valid per_page is respected.
        items = list(range(50))
        p = Paginator(items, per_page=20)
        result = p.get_page(1, per_page=5)
        assert result.per_page == 5
        assert len(result.items) == 5

    def test_paginator_total_pages_zero_per_page_no_raise(self):
        # Guard path: per_page=0 must not raise; clamps to 1 item/page.
        p = Paginator([1, 2, 3], per_page=0)
        assert p.total_pages == 3

    def test_paginator_total_pages_zero_per_page_empty(self):
        # Guard path: empty collection + per_page=0 -> 1 page, no raise.
        p = Paginator([], per_page=0)
        assert p.total_pages == 1

    def test_paginator_total_pages_matches_iterate_pages_zero_per_page(self):
        # Consistency: total_pages agrees with iterate_pages for per_page=0.
        p = Paginator([1, 2, 3], per_page=0)
        assert p.total_pages == len(p.iterate_pages())

    def test_paginator_get_page_zero_per_page_clamps(self):
        # Guard path: get_page clamps per_page=0 to 1 (unchanged).
        p = Paginator([1, 2, 3], per_page=0)
        result = p.get_page(1)
        assert result.per_page == 1
        assert result.items == [1]

    def test_paginator_total_pages_normal_unchanged(self):
        # Normal case: a valid per_page is respected (unchanged).
        p = Paginator([1, 2, 3, 4, 5], per_page=2)
        assert p.total_pages == 3


class TestIteratePagesContract:
    """Pin the exact contract of Paginator.iterate_pages (TICKET-501)."""

    def test_returns_list_of_pageresult(self):
        pages = Paginator(list(range(5))).iterate_pages()
        assert isinstance(pages, list)
        assert all(isinstance(p, PageResult) for p in pages)

    def test_empty_collection_yields_one_page(self):
        pages = Paginator([]).iterate_pages()
        assert len(pages) == 1
        assert pages[0].items == []
        assert pages[0].total == 0
        assert pages[0].total_pages == 1

    def test_per_page_override_affects_page_count(self):
        pages = Paginator(list(range(10))).iterate_pages(per_page=3)
        assert len(pages) == 4
        assert [len(p.items) for p in pages] == [3, 3, 3, 1]
        # total_pages reflects the override, not the constructor default
        assert pages[-1].total_pages == 4

    def test_per_page_override_slices_correctly(self):
        pages = Paginator(list(range(10))).iterate_pages(per_page=4)
        assert [p.items for p in pages] == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

    def test_pages_in_order(self):
        pages = Paginator(list(range(10)), per_page=3).iterate_pages()
        assert [p.page for p in pages] == [1, 2, 3, 4]

    def test_partial_last_page(self):
        pages = Paginator(list(range(10)), per_page=3).iterate_pages()
        assert len(pages[-1].items) == 1
