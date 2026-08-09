"""Tests for content pagination - paginate search results."""

import pytest
from personal_index.content_pagination import (
    PaginationConfig,
    PaginationResult,
    ContentPaginator,
    PageCursor,
    PaginationMeta,
)


class TestPaginationConfig:
    def test_default_config(self):
        config = PaginationConfig()
        assert config.page == 1
        assert config.per_page == 20
        assert config.max_per_page == 100

    def test_custom_page(self):
        config = PaginationConfig(page=3, per_page=10)
        assert config.page == 3
        assert config.per_page == 10

    def test_page_clamped_to_min(self):
        config = PaginationConfig(page=0)
        assert config.page == 1

    def test_page_clamped_to_negative(self):
        config = PaginationConfig(page=-1)
        assert config.page == 1

    def test_per_page_capped(self):
        config = PaginationConfig(per_page=200)
        assert config.per_page == 100

    def test_per_page_min(self):
        config = PaginationConfig(per_page=0)
        assert config.per_page == 1

    def test_offset_calculation(self):
        config = PaginationConfig(page=3, per_page=10)
        assert config.offset == 20

    def test_limit_calculation(self):
        config = PaginationConfig(page=2, per_page=15)
        assert config.limit == 15

    def test_to_dict(self):
        config = PaginationConfig(page=2, per_page=10)
        d = config.to_dict()
        assert d["page"] == 2
        assert d["per_page"] == 10

    def test_from_dict(self):
        d = {"page": 3, "per_page": 25}
        config = PaginationConfig.from_dict(d)
        assert config.page == 3
        assert config.per_page == 25


class TestPageCursor:
    def test_default_cursor(self):
        cursor = PageCursor()
        assert cursor.page == 1
        assert cursor.per_page == 20

    def test_custom_cursor(self):
        cursor = PageCursor(page=5, per_page=10)
        assert cursor.page == 5
        assert cursor.per_page == 10

    def test_cursor_to_string_returns_base64(self):
        cursor = PageCursor(page=3, per_page=10)
        s = cursor.to_string()
        assert len(s) > 0
        # Verify it can be decoded back
        decoded = PageCursor.from_string(s)
        assert decoded.page == 3
        assert decoded.per_page == 10

    def test_cursor_from_string(self):
        cursor = PageCursor(page=3, per_page=10)
        encoded = cursor.to_string()
        c = PageCursor.from_string(encoded)
        assert c.page == 3
        assert c.per_page == 10

    def test_cursor_from_invalid_string(self):
        c = PageCursor.from_string("invalid!!!")
        assert c.page == 1
        assert c.per_page == 20

    def test_cursor_next(self):
        cursor = PageCursor(page=2, per_page=10)
        next_cursor = cursor.next()
        assert next_cursor.page == 3

    def test_cursor_prev(self):
        cursor = PageCursor(page=3, per_page=10)
        prev_cursor = cursor.prev()
        assert prev_cursor.page == 2

    def test_cursor_prev_at_first(self):
        cursor = PageCursor(page=1, per_page=10)
        prev_cursor = cursor.prev()
        assert prev_cursor.page == 1


class TestPaginationMeta:
    def test_total_pages(self):
        meta = PaginationMeta(total=100, page=1, per_page=20)
        assert meta.total_pages == 5

    def test_has_next(self):
        meta = PaginationMeta(total=100, page=1, per_page=20)
        assert meta.has_next is True

    def test_no_next_on_last_page(self):
        meta = PaginationMeta(total=100, page=5, per_page=20)
        assert meta.has_next is False

    def test_has_prev(self):
        meta = PaginationMeta(total=100, page=2, per_page=20)
        assert meta.has_prev is True

    def test_no_prev_on_first_page(self):
        meta = PaginationMeta(total=100, page=1, per_page=20)
        assert meta.has_prev is False

    def test_next_page_number(self):
        meta = PaginationMeta(total=100, page=2, per_page=20)
        assert meta.next_page == 3

    def test_prev_page_number(self):
        meta = PaginationMeta(total=100, page=3, per_page=20)
        assert meta.prev_page == 2

    def test_start_index(self):
        meta = PaginationMeta(total=100, page=2, per_page=20)
        assert meta.start_index == 21

    def test_end_index(self):
        meta = PaginationMeta(total=100, page=2, per_page=20)
        assert meta.end_index == 40

    def test_end_index_last_page(self):
        meta = PaginationMeta(total=95, page=5, per_page=20)
        assert meta.end_index == 95

    def test_to_dict(self):
        meta = PaginationMeta(total=50, page=2, per_page=10)
        d = meta.to_dict()
        assert d["total"] == 50
        assert d["total_pages"] == 5
        assert d["has_next"] is True


class TestPaginationResult:
    def test_basic_result(self):
        result = PaginationResult(items=["a", "b"], total=10, page=1, per_page=2)
        assert len(result.items) == 2
        assert result.total == 10
        assert result.page == 1

    def test_total_pages(self):
        result = PaginationResult(items=[], total=100, page=1, per_page=20)
        assert result.total_pages == 5

    def test_has_next(self):
        result = PaginationResult(items=[], total=100, page=1, per_page=20)
        assert result.has_next is True

    def test_has_prev(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20)
        assert result.has_prev is True

    def test_next_page(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20)
        assert result.next_page == 3

    def test_prev_page(self):
        result = PaginationResult(items=[], total=100, page=3, per_page=20)
        assert result.prev_page == 2

    def test_start_index(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20)
        assert result.start_index == 21

    def test_end_index(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20)
        assert result.end_index == 40

    def test_to_dict(self):
        result = PaginationResult(items=["x"], total=10, page=1, per_page=5)
        d = result.to_dict()
        assert d["total"] == 10
        assert d["total_pages"] == 2
        assert d["page"] == 1

    def test_links(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20, base_url="/api/search")
        assert "next" in result.links
        assert "prev" in result.links

    def test_links_no_prev(self):
        result = PaginationResult(items=[], total=100, page=1, per_page=20, base_url="/api/search")
        assert "prev" not in result.links

    def test_links_no_next(self):
        result = PaginationResult(items=[], total=100, page=5, per_page=20, base_url="/api/search")
        assert "next" not in result.links

    def test_links_first_last(self):
        result = PaginationResult(items=[], total=100, page=2, per_page=20, base_url="/api/search")
        assert "first" in result.links
        assert "last" in result.links


class TestContentPaginator:
    def test_first_page(self):
        items = list(range(50))
        paginator = ContentPaginator(items)
        result = paginator.get_page(1, per_page=10)
        assert len(result.items) == 10
        assert result.items[0] == 0

    def test_second_page(self):
        items = list(range(50))
        paginator = ContentPaginator(items)
        result = paginator.get_page(2, per_page=10)
        assert len(result.items) == 10
        assert result.items[0] == 10

    def test_last_page(self):
        items = list(range(50))
        paginator = ContentPaginator(items)
        result = paginator.get_page(5, per_page=10)
        assert len(result.items) == 10
        assert result.items[0] == 40

    def test_partial_last_page(self):
        items = list(range(55))
        paginator = ContentPaginator(items)
        result = paginator.get_page(6, per_page=10)
        assert len(result.items) == 5

    def test_out_of_range_page(self):
        items = list(range(10))
        paginator = ContentPaginator(items, per_page=5)
        result = paginator.get_page(100)
        assert len(result.items) == 0

    def test_total_items(self):
        items = list(range(100))
        paginator = ContentPaginator(items)
        assert paginator.total_items == 100

    def test_total_pages(self):
        items = list(range(95))
        paginator = ContentPaginator(items, per_page=20)
        assert paginator.total_pages == 5

    def test_iterate_pages(self):
        items = list(range(25))
        paginator = ContentPaginator(items, per_page=10)
        pages = list(paginator.iterate_pages())
        assert len(pages) == 3
        assert len(pages[0].items) == 10
        assert len(pages[2].items) == 5

    def test_single_item(self):
        items = ["only"]
        paginator = ContentPaginator(items)
        result = paginator.get_page(1)
        assert len(result.items) == 1
        assert result.total_pages == 1

    def test_empty_items(self):
        paginator = ContentPaginator([])
        result = paginator.get_page(1)
        assert len(result.items) == 0
        assert result.total_pages == 1

    def test_with_config(self):
        items = list(range(100))
        paginator = ContentPaginator(items)
        config = PaginationConfig(page=3, per_page=10)
        result = paginator.get_page_with_config(config)
        assert len(result.items) == 10
        assert result.items[0] == 20

    def test_with_cursor(self):
        items = list(range(100))
        paginator = ContentPaginator(items, per_page=10)
        cursor = PageCursor(page=2, per_page=10)
        result = paginator.get_page_with_cursor(cursor)
        assert len(result.items) == 10
        assert result.items[0] == 10

    def test_page_range(self):
        items = list(range(100))
        paginator = ContentPaginator(items, per_page=10)
        result = paginator.get_page(3, per_page=10)
        assert result.start_index == 21
        assert result.end_index == 30

    def test_preserves_item_data(self):
        items = [{"title": f"Item {i}", "score": i} for i in range(50)]
        paginator = ContentPaginator(items, per_page=10)
        result = paginator.get_page(2)
        assert result.items[0]["title"] == "Item 10"
        assert result.items[0]["score"] == 10

    def test_page_clamping(self):
        items = list(range(10))
        paginator = ContentPaginator(items, per_page=5)
        result = paginator.get_page(0)
        assert len(result.items) == 5
        assert result.page == 1

    def test_per_page_capping(self):
        items = list(range(100))
        paginator = ContentPaginator(items, per_page=10, max_per_page=20)
        result = paginator.get_page(1, per_page=50)
        assert len(result.items) == 20
