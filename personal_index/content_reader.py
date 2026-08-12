"""Content reader module for personal-index.

Provides utilities for reading, navigating, and browsing indexed content
with support for pagination, filtering, and formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReadResult:
    """Result of reading content."""
    url: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class PageView:
    """A paginated view of content items."""
    items: list[ReadResult]
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


class ContentReader:
    """Reader for navigating and browsing indexed content.

    Provides pagination, filtering by tags/score, and formatting
    options for displaying content.
    """

    def __init__(self):
        self._items: list[ReadResult] = []
        self._url_index: dict[str, ReadResult] = {}

    def add(self, item: ReadResult) -> None:
        """Add a content item."""
        self._items.append(item)
        self._url_index[item.url] = item

    def add_many(self, items: list[ReadResult]) -> None:
        """Add multiple content items."""
        for item in items:
            self.add(item)

    def get(self, url: str) -> ReadResult | None:
        """Get a content item by URL."""
        return self._url_index.get(url)

    def list_all(self) -> list[ReadResult]:
        """List all content items."""
        return list(self._items)

    def paginate(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "score",
        reverse: bool = True,
    ) -> PageView:
        """Get a paginated view of content items.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Field to sort by ('score', 'title', 'url').
            reverse: Sort in descending order.

        Returns:
            PageView with paginated results.
        """
        items = list(self._items)

        # Sort
        if sort_by == "score":
            items.sort(key=lambda x: x.score, reverse=reverse)
        elif sort_by == "title":
            items.sort(key=lambda x: x.title.lower(), reverse=reverse)
        elif sort_by == "url":
            items.sort(key=lambda x: x.url.lower(), reverse=reverse)

        total_items = len(items)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return PageView(
            items=page_items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    def filter_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
    ) -> list[ReadResult]:
        """Filter content items by tags.

        Args:
            tags: Tags to filter by.
            match_all: If True, item must have all tags. If False, any tag.

        Returns:
            Filtered list of ReadResult items.
        """
        if not tags:
            return list(self._items)

        tag_set = {t.lower() for t in tags}
        results = []
        for item in self._items:
            item_tags = {t.lower() for t in item.tags}
            if match_all:
                if tag_set.issubset(item_tags):
                    results.append(item)
            else:
                if tag_set & item_tags:
                    results.append(item)
        return results

    def filter_by_score(
        self,
        min_score: float = 0.0,
        max_score: float | None = None,
    ) -> list[ReadResult]:
        """Filter content items by score range.

        Args:
            min_score: Minimum score (inclusive).
            max_score: Maximum score (inclusive), or None for no upper bound.

        Returns:
            Filtered list of ReadResult items.
        """
        results = []
        for item in self._items:
            if item.score >= min_score and (max_score is None or item.score <= max_score):
                results.append(item)
        return results

    def search_titles(self, query: str) -> list[ReadResult]:
        """Search content items by title text.

        Args:
            query: Search query (case-insensitive substring match).

        Returns:
            Matching ReadResult items.
        """
        query_lower = query.lower()
        return [
            item for item in self._items
            if query_lower in item.title.lower()
        ]

    def search_content(self, query: str) -> list[ReadResult]:
        """Search content items by content text.

        Args:
            query: Search query (case-insensitive substring match).

        Returns:
            Matching ReadResult items.
        """
        query_lower = query.lower()
        return [
            item for item in self._items
            if query_lower in item.content.lower()
        ]

    def format_item(self, item: ReadResult, show_content: bool = True) -> str:
        """Format a content item for display.

        Args:
            item: The ReadResult to format.
            show_content: Whether to include content text.

        Returns:
            Formatted string representation.
        """
        lines = [
            f"## {item.title}",
            f"URL: {item.url}",
            f"Score: {item.score:.2f}",
        ]
        if item.tags:
            lines.append(f"Tags: {', '.join(item.tags)}")
        if show_content and item.content:
            lines.append("")
            lines.append(item.content[:500])
            if len(item.content) > 500:
                lines.append("...")
        return "\n".join(lines)

    def format_page(self, page_view: PageView, show_content: bool = True) -> str:
        """Format a paginated view for display.

        Args:
            page_view: The PageView to format.
            show_content: Whether to include content text.

        Returns:
            Formatted string with pagination info and items.
        """
        lines = [
            f"Page {page_view.page} of {page_view.total_pages}",
            f"Showing {page_view.start_index + 1}-{page_view.end_index} of {page_view.total_items} items",
            "",
        ]
        for item in page_view.items:
            lines.append(self.format_item(item, show_content))
            lines.append("---")
            lines.append("")

        nav = []
        if page_view.has_prev:
            nav.append(f"[Prev Page {page_view.page - 1}]")
        if page_view.has_next:
            nav.append(f"[Next Page {page_view.page + 1}]")
        if nav:
            lines.append(" | ".join(nav))

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all content items."""
        self._items.clear()
        self._url_index.clear()

    @property
    def count(self) -> int:
        """Number of content items."""
        return len(self._items)
