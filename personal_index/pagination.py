"""Pagination utilities for search and browse results."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PageParams:
    """Parameters for pagination."""

    page: int = 1
    per_page: int = 20
    max_per_page: int = 100

    def __post_init__(self):
        self.page = max(1, self.page)
        self.per_page = max(1, min(self.per_page, self.max_per_page))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


@dataclass
class PageResult:
    """Paginated result set."""

    items: list[Any]
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.per_page))

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def next_page(self) -> Optional[int]:
        return self.page + 1 if self.has_next else None

    @property
    def prev_page(self) -> Optional[int]:
        return self.page - 1 if self.has_prev else None

    @property
    def start_index(self) -> int:
        return (self.page - 1) * self.per_page + 1

    @property
    def end_index(self) -> int:
        return min(self.page * self.per_page, self.total)

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_page": self.next_page,
            "prev_page": self.prev_page,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


class Paginator:
    """Paginates a collection of items."""

    def __init__(self, items: list[Any], per_page: int = 20, max_per_page: int = 100):
        self._items = items
        self._per_page = per_page
        self._max_per_page = max_per_page

    def get_page(self, page: int = 1, per_page: Optional[int] = None) -> PageResult:
        params = PageParams(
            page=page,
            per_page=per_page or self._per_page,
            max_per_page=self._max_per_page,
        )
        start = params.offset
        end = start + params.limit
        page_items = self._items[start:end]
        return PageResult(
            items=page_items,
            total=len(self._items),
            page=params.page,
            per_page=params.per_page,
        )

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self._items) / self._per_page))

    def iterate_pages(self, per_page: Optional[int] = None) -> list[PageResult]:
        """Get all pages as a list."""
        pages = []
        page_num = 1
        while True:
            result = self.get_page(page_num, per_page)
            pages.append(result)
            if not result.has_next:
                break
            page_num += 1
        return pages
