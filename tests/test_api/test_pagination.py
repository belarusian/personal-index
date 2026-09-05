"""Tests for API pagination utilities."""

from __future__ import annotations

import pytest

from personal_index.api.pagination import (
    PageInfo,
    paginate,
    paginate_with_offset,
)


class TestPageInfo:
    def test_page_info(self):
        info = PageInfo(page=1, page_size=10, total_items=25, total_pages=3,
                        has_next=True, has_prev=False)
        assert info.start_index == 0
        assert info.end_index == 10

    def test_page_info_page_2(self):
        info = PageInfo(page=2, page_size=10, total_items=25, total_pages=3,
                        has_next=True, has_prev=True)
        assert info.start_index == 10
        assert info.end_index == 20

    def test_to_dict(self):
        info = PageInfo(page=1, page_size=10, total_items=5, total_pages=1,
                        has_next=False, has_prev=False)
        data = info.to_dict()
        assert data["page"] == 1
        assert data["total_pages"] == 1


class TestPaginate:
    def test_first_page(self):
        items = list(range(25))
        result = paginate(items, page=1, page_size=10)
        assert result.items == list(range(10))
        assert result.page_info.total_items == 25
        assert result.page_info.total_pages == 3
        assert result.page_info.has_next is True
        assert result.page_info.has_prev is False

    def test_middle_page(self):
        items = list(range(25))
        result = paginate(items, page=2, page_size=10)
        assert result.items == list(range(10, 20))
        assert result.page_info.has_next is True
        assert result.page_info.has_prev is True

    def test_last_page(self):
        items = list(range(25))
        result = paginate(items, page=3, page_size=10)
        assert result.items == list(range(20, 25))
        assert result.page_info.has_next is False
        assert result.page_info.has_prev is True

    def test_single_page(self):
        items = list(range(5))
        result = paginate(items, page=1, page_size=10)
        assert result.items == list(range(5))
        assert result.page_info.total_pages == 1
        assert result.page_info.has_next is False

    def test_empty_items(self):
        result = paginate([], page=1, page_size=10)
        assert result.items == []
        assert result.page_info.total_items == 0
        assert result.page_info.total_pages == 1

    def test_page_clamped_to_max(self):
        items = list(range(10))
        result = paginate(items, page=999, page_size=10)
        assert result.page_info.page == 1
        assert result.items == list(range(10))

    def test_invalid_page(self):
        with pytest.raises(ValueError, match="Page must be >= 1"):
            paginate([1, 2, 3], page=0, page_size=10)

    def test_invalid_page_size(self):
        with pytest.raises(ValueError, match="Page size must be >= 1"):
            paginate([1, 2, 3], page=1, page_size=0)

    def test_to_dict_with_objects(self):
        from personal_index.models import IndexedPage
        pages = [IndexedPage(url=f"http://example.com/{i}", title=f"Page {i}")
                 for i in range(5)]
        result = paginate(pages, page=1, page_size=3)
        data = result.to_dict()
        assert len(data["items"]) == 3
        assert data["items"][0]["url"] == "http://example.com/0"

    def test_exact_page_boundary(self):
        items = list(range(20))
        result = paginate(items, page=2, page_size=10)
        assert result.items == list(range(10, 20))
        assert result.page_info.has_next is False


class TestPaginateWithOffset:
    def test_offset_zero(self):
        items = list(range(25))
        result = paginate_with_offset(items, offset=0, limit=10)
        assert result.items == list(range(10))
        assert result.page_info.has_next is True
        assert result.page_info.has_prev is False

    def test_offset_middle(self):
        items = list(range(25))
        result = paginate_with_offset(items, offset=10, limit=10)
        assert result.items == list(range(10, 20))
        assert result.page_info.has_next is True
        assert result.page_info.has_prev is True

    def test_offset_past_end(self):
        items = list(range(10))
        result = paginate_with_offset(items, offset=20, limit=10)
        assert result.items == []

    def test_negative_offset(self):
        with pytest.raises(ValueError, match="Offset must be >= 0"):
            paginate_with_offset([1, 2], offset=-1, limit=10)

    def test_invalid_limit(self):
        with pytest.raises(ValueError, match="Limit must be >= 1"):
            paginate_with_offset([1, 2], offset=0, limit=0)

    def test_to_dict(self):
        items = [{"id": i} for i in range(5)]
        result = paginate_with_offset(items, offset=0, limit=3)
        data = result.to_dict()
        assert len(data["items"]) == 3
        assert data["page_info"]["total_items"] == 5


class TestPaginatePinning:
    """Pin the returned PaginatedResult/PageInfo fields for the normal case
    and the empty-sequence guard path (TICKET-433)."""

    def test_normal_page_pins_returned_fields(self):
        items = list(range(25))
        result = paginate(items, page=2, page_size=10)
        # items slice for page 2 of 3
        assert result.items == list(range(10, 20))
        pi = result.page_info
        assert pi.page == 2
        assert pi.page_size == 10
        assert pi.total_items == 25
        assert pi.total_pages == 3
        assert pi.has_next is True
        assert pi.has_prev is True
        # derived properties
        assert pi.start_index == 10
        assert pi.end_index == 20

    def test_empty_sequence_guard_pins_returned_fields(self):
        result = paginate([], page=1, page_size=10)
        assert result.items == []
        pi = result.page_info
        # empty-sequence clamp forces page to 1, total_pages to 1
        assert pi.page == 1
        assert pi.page_size == 10
        assert pi.total_items == 0
        assert pi.total_pages == 1
        assert pi.has_next is False
        assert pi.has_prev is False
        assert pi.start_index == 0
        assert pi.end_index == 0
