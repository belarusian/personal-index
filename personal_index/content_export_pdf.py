"""Content PDF export for personal-index.

Exports saved content as PDF documents with configurable layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PDFPageLayout(str, Enum):
    """Supported page layouts for PDF export."""

    A4 = "a4"
    LETTER = "letter"
    LEGAL = "legal"

    @property
    def width_mm(self) -> int:
        """Page width in millimeters."""
        dimensions = {
            "a4": (210, 297),
            "letter": (216, 279),
            "legal": (216, 356),
        }
        return dimensions[self.value][0]

    @property
    def height_mm(self) -> int:
        """Page height in millimeters."""
        dimensions = {
            "a4": (210, 297),
            "letter": (216, 279),
            "legal": (216, 356),
        }
        return dimensions[self.value][1]


@dataclass
class PDFExportConfig:
    """Configuration for PDF export."""

    title: str = "Content Export"
    author: str = "personal-index"
    page_layout: PDFPageLayout = PDFPageLayout.A4
    include_cover: bool = True
    include_toc: bool = True
    items_per_page: int = 10
    font_size: int = 11
    margin_mm: int = 20
    include_timestamps: bool = True
    include_word_counts: bool = True
    sort_by: str = "title"
    sort_reverse: bool = False

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "page_layout": self.page_layout.value,
            "include_cover": self.include_cover,
            "include_toc": self.include_toc,
            "items_per_page": self.items_per_page,
            "font_size": self.font_size,
            "margin_mm": self.margin_mm,
            "include_timestamps": self.include_timestamps,
            "include_word_counts": self.include_word_counts,
            "sort_by": self.sort_by,
            "sort_reverse": self.sort_reverse,
        }


@dataclass
class PDFContentItem:
    """A content item formatted for PDF export."""

    url: str
    title: str
    content: str = ""
    word_count: int = 0
    category: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: Optional[str] = None
    engagement_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "engagement_score": self.engagement_score,
        }

    def truncate_content(self, max_length: int = 500) -> str:
        """Truncate content to max_length characters (including ellipsis)."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[: max_length - 3] + "..."

    def format_for_pdf(self, config: PDFExportConfig) -> str:
        """Format item as text for PDF inclusion."""
        lines = [f"## {self.title}", f"URL: {self.url}"]
        if config.include_word_counts and self.word_count:
            lines.append(f"Word count: {self.word_count}")
        if self.category:
            lines.append(f"Category: {self.category}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        if config.include_timestamps and self.created_at:
            lines.append(f"Saved: {self.created_at}")
        if self.engagement_score > 0:
            lines.append(f"Engagement score: {self.engagement_score:.1f}")
        lines.append("")
        lines.append(self.truncate_content(500))
        return "\n".join(lines)


@dataclass
class PDFExportResult:
    """Result of a PDF export operation."""

    success: bool = True
    items_exported: int = 0
    total_pages: int = 0
    output: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    exported_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "items_exported": self.items_exported,
            "total_pages": self.total_pages,
            "exported_at": self.exported_at,
            "errors": self.errors,
        }


class PDFExporter:
    """Exports content items as PDF-formatted text."""

    def __init__(self, config: Optional[PDFExportConfig] = None) -> None:
        self.config = config or PDFExportConfig()

    def _sort_items(self, items: list[PDFContentItem]) -> list[PDFContentItem]:
        """Sort items according to config."""
        key_map = {
            "title": lambda x: x.title.lower(),
            "url": lambda x: x.url.lower(),
            "word_count": lambda x: x.word_count,
            "engagement_score": lambda x: x.engagement_score,
            "created_at": lambda x: x.created_at or "",
            "category": lambda x: x.category.lower(),
        }
        sort_key = key_map.get(self.config.sort_by, key_map["title"])
        return sorted(items, key=sort_key, reverse=self.config.sort_reverse)

    def _generate_cover_page(self) -> str:
        """Generate cover page content."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            "",
            "=" * 60,
            "",
            f"  {self.config.title}",
            "",
            f"  Author: {self.config.author}",
            f"  Generated: {now}",
            f"  Page Layout: {self.config.page_layout.value.upper()}",
            "",
            "=" * 60,
            "",
        ]
        return "\n".join(lines)

    def _generate_toc(self, items: list[PDFContentItem]) -> str:
        """Generate table of contents."""
        lines = ["", "TABLE OF CONTENTS", "=" * 40, ""]
        for i, item in enumerate(items, 1):
            lines.append(f"  {i}. {item.title}")
        lines.append("")
        return "\n".join(lines)

    def _paginate(self, items: list[PDFContentItem]) -> list[list[PDFContentItem]]:
        """Split items into pages."""
        pages = []
        for i in range(0, len(items), self.config.items_per_page):
            pages.append(items[i : i + self.config.items_per_page])
        return pages

    def export(
        self, items: list[PDFContentItem]
    ) -> PDFExportResult:
        """Export items to PDF-formatted text."""
        try:
            if not items:
                return PDFExportResult(
                    success=True,
                    items_exported=0,
                    total_pages=0,
                    output="",
                )

            sorted_items = self._sort_items(items)
            pages = self._paginate(sorted_items)

            output_parts = []

            # Cover page
            if self.config.include_cover:
                output_parts.append(self._generate_cover_page())

            # Table of contents
            if self.config.include_toc:
                output_parts.append(self._generate_toc(sorted_items))

            # Content pages
            for page_num, page_items in enumerate(pages, 1):
                page_header = f"\n--- Page {page_num} ---\n"
                output_parts.append(page_header)
                for item in page_items:
                    output_parts.append(item.format_for_pdf(self.config))
                    output_parts.append("")

            output = "\n".join(output_parts)
            return PDFExportResult(
                success=True,
                items_exported=len(sorted_items),
                total_pages=len(pages),
                output=output,
            )

        except Exception as e:
            return PDFExportResult(
                success=False,
                items_exported=0,
                total_pages=0,
                errors=[str(e)],
            )

    def export_from_dicts(
        self, items: list[dict]
    ) -> PDFExportResult:
        """Export items from raw dictionaries."""
        pdf_items = []
        for item in items:
            pdf_items.append(PDFContentItem(
                url=item.get("url", ""),
                title=item.get("title", "Untitled"),
                content=item.get("content", ""),
                word_count=item.get("word_count", 0),
                category=item.get("category", ""),
                tags=item.get("tags", []),
                created_at=item.get("created_at"),
                engagement_score=item.get("engagement_score", 0.0),
            ))
        return self.export(pdf_items)
