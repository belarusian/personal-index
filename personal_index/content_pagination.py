"""Paginate search results and content listings."""

from __future__ import annotations

import base64
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PaginationConfig:
    """Configuration for pagination."""
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

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "per_page": self.per_page,
            "max_per_page": self.max_per_page,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaginationConfig":
        return cls(
            page=data.get("page", 1),
            per_page=data.get("per_page", 20),
            max_per_page=data.get("max_per_page", 100),
        )


@dataclass
class PageCursor:
    """Cursor-based pagination pointer."""
    page: int = 1
    per_page: int = 20

    def to_string(self) -> str:
        data = json.dumps({"page": self.page, "per_page": self.per_page})
        return base64.b64encode(data.encode()).decode()

    @classmethod
    def from_string(cls, cursor_str: str) -> "PageCursor":
        try:
            data = json.loads(base64.b64decode(cursor_str).decode())
            return cls(page=data.get("page", 1), per_page=data.get("per_page", 20))
        except Exception:
            return cls()

    def next(self) -> "PageCursor":
        return PageCursor(page=self.page + 1, per_page=self.per_page)

    def prev(self) -> "PageCursor":
        return PageCursor(page=max(1, self.page - 1), per_page=self.per_page)


@dataclass
class PaginationMeta:
    """Metadata about pagination state."""
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


@dataclass
class PaginationResult:
    """Paginated result set with metadata."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    base_url: str = ""

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

    @property
    def links(self) -> Dict[str, str]:
        links = {}
        if self.base_url:
            if self.has_next:
                links["next"] = f"{self.base_url}?page={self.page + 1}&per_page={self.per_page}"
            if self.has_prev:
                links["prev"] = f"{self.base_url}?page={self.page - 1}&per_page={self.per_page}"
            links["first"] = f"{self.base_url}?page=1&per_page={self.per_page}"
            links["last"] = f"{self.base_url}?page={self.total_pages}&per_page={self.per_page}"
        return links

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
            "links": self.links,
        }


class ContentPaginator:
    """Paginates a collection of content items."""

    def __init__(self, items: List[Any], per_page: int = 20, max_per_page: int = 100):
        self._items = items
        self._per_page = per_page
        self._max_per_page = max_per_page

    def get_page(self, page: int = 1, per_page: Optional[int] = None) -> PaginationResult:
        config = PaginationConfig(
            page=page,
            per_page=per_page or self._per_page,
            max_per_page=self._max_per_page,
        )
        start = config.offset
        end = start + config.limit
        page_items = self._items[start:end]
        return PaginationResult(
            items=page_items,
            total=len(self._items),
            page=config.page,
            per_page=config.per_page,
        )

    def get_page_with_config(self, config: PaginationConfig) -> PaginationResult:
        """Get a page using a PaginationConfig."""
        return self.get_page(page=config.page, per_page=config.per_page)

    def get_page_with_cursor(self, cursor: PageCursor) -> PaginationResult:
        """Get a page using a PageCursor."""
        return self.get_page(page=cursor.page, per_page=cursor.per_page)

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self._items) / self._per_page))

    def iterate_pages(self, per_page: Optional[int] = None) -> List[PaginationResult]:
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
