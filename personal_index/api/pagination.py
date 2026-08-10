"""Pagination utilities for the personal-index API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Sequence, TypeVar

T = TypeVar("T")


@dataclass
class PageInfo:
    """Pagination metadata."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @property
    def start_index(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def end_index(self) -> int:
        return min(self.start_index + self.page_size, self.total_items)

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


@dataclass
class PaginatedResult(Generic[T]):
    """A paginated result set."""
    items: List[T]
    page_info: PageInfo

    def to_dict(self) -> dict:
        items_data = []
        for item in self.items:
            if hasattr(item, "to_dict"):
                items_data.append(item.to_dict())
            elif isinstance(item, dict):
                items_data.append(item)
            else:
                items_data.append(item)
        return {
            "items": items_data,
            "page_info": self.page_info.to_dict(),
        }


def paginate(
    items: Sequence[T],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResult[T]:
    """Paginate a sequence of items.

    Args:
        items: The full sequence of items.
        page: 1-based page number.
        page_size: Number of items per page.

    Returns:
        PaginatedResult with items and page info.

    Raises:
        ValueError: If page or page_size is invalid.
    """
    if page < 1:
        raise ValueError("Page must be >= 1")
    if page_size < 1:
        raise ValueError("Page size must be >= 1")

    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)

    # Clamp page to valid range
    page = max(1, min(page, total_pages)) if total_items > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    page_items = list(items[start:end])

    page_info = PageInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return PaginatedResult(items=page_items, page_info=page_info)


def paginate_with_offset(
    items: Sequence[T],
    offset: int = 0,
    limit: int = 20,
) -> PaginatedResult[T]:
    """Paginate using offset/limit instead of page numbers.

    Args:
        items: The full sequence of items.
        offset: Starting index (0-based).
        limit: Maximum number of items to return.

    Returns:
        PaginatedResult with items and page info.
    """
    if offset < 0:
        raise ValueError("Offset must be >= 0")
    if limit < 1:
        raise ValueError("Limit must be >= 1")

    total_items = len(items)
    page = (offset // limit) + 1 if limit > 0 else 1
    total_pages = max(1, (total_items + limit - 1) // limit)

    end = offset + limit
    page_items = list(items[offset:end])

    page_info = PageInfo(
        page=page,
        page_size=limit,
        total_items=total_items,
        total_pages=total_pages,
        has_next=end < total_items,
        has_prev=offset > 0,
    )

    return PaginatedResult(items=page_items, page_info=page_info)
