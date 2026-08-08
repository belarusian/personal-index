"""Tests for pagination utilities."""

import pytest
from personal_index.pagination import Paginator, PageParams, PageResult


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

    def test_has_next(self):
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.has_next is True
        r2 = PageResult(items=[], total=100, page=5, per_page=20)
        assert r2.has_next is False

    def test_has_prev(self):
        r = PageResult(items=[], total=100, page=1, per_page=20)
        assert r.has_prev is False
        r2 = PageResult(items=[], total=100, page=2, per_page=20)
        assert r2.has_prev is True

    def test_next_prev_page(self):
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.next_page == 3
        assert r.prev_page == 1

    def test_start_end_index(self):
        r = PageResult(items=[], total=100, page=2, per_page=20)
        assert r.start_index == 21
        assert r.end_index == 40

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
