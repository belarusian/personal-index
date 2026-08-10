"""Export content as markdown, HTML, and plain text formats."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"


@dataclass
class ExportConfig:
    """Configuration for content export."""

    include_metadata: bool = True
    include_tags: bool = True
    include_summary: bool = False
    sort_by: str = "date"
    group_by: Optional[str] = None

    _VALID_SORT = {"date", "title", "priority", "relevance"}
    _VALID_GROUP = {"tags", "date", "category", None}

    def __post_init__(self) -> None:
        if self.sort_by not in self._VALID_SORT:
            raise ValueError(
                f"Invalid sort_by '{self.sort_by}'. Must be one of: {self._VALID_SORT}"
            )
        if self.group_by not in self._VALID_GROUP:
            raise ValueError(
                f"Invalid group_by '{self.group_by}'. Must be one of: {self._VALID_GROUP}"
            )


class MarkdownExporter:
    """Export saved content as markdown, HTML, or plain text.

    Supports sorting by date, title, or priority, grouping by tags
    or date, and optional metadata/tags/summary inclusion.
    """

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        self.config = config or ExportConfig()

    def export(
        self,
        items: list[dict[str, Any]],
        format: Optional[ExportFormat] = None,
    ) -> str:
        """Export content items to the specified format.

        Args:
            items: List of content item dicts.
            format: Export format (defaults to markdown).

        Returns:
            Formatted export string.
        """
        if not items:
            return ""

        use_format = format or ExportFormat.MARKDOWN
        sorted_items = self._sort_items(items)

        if use_format == ExportFormat.MARKDOWN:
            return self._export_markdown(sorted_items)
        elif use_format == ExportFormat.HTML:
            return self._export_html(sorted_items)
        elif use_format == ExportFormat.PLAIN_TEXT:
            return self._export_plain_text(sorted_items)
        else:
            return self._export_markdown(sorted_items)

    def _sort_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort items based on configuration."""
        if self.config.sort_by == "date":
            return sorted(
                items,
                key=lambda x: x.get("published_date", ""),
                reverse=True,
            )
        elif self.config.sort_by == "title":
            return sorted(items, key=lambda x: x.get("title", "").lower())
        elif self.config.sort_by == "priority":
            return sorted(
                items,
                key=lambda x: x.get("priority_score", 0),
                reverse=True,
            )
        elif self.config.sort_by == "relevance":
            return sorted(
                items,
                key=lambda x: x.get("relevance_score", 0),
                reverse=True,
            )
        return items

    def _group_items(
        self, items: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group items based on configuration."""
        if not self.config.group_by:
            return {"all": items}

        groups: dict[str, list[dict[str, Any]]] = {}

        if self.config.group_by == "tags":
            for item in items:
                tags = item.get("tags", [])
                if tags:
                    for tag in tags:
                        tag_key = tag.lower()
                        groups.setdefault(tag_key, []).append(item)
                else:
                    groups.setdefault("untagged", []).append(item)
        elif self.config.group_by == "date":
            for item in items:
                date_str = item.get("published_date", "")
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str)
                        group_key = dt.strftime("%Y-%m")
                    except (ValueError, TypeError):
                        group_key = "unknown"
                else:
                    group_key = "unknown"
                groups.setdefault(group_key, []).append(item)
        elif self.config.group_by == "category":
            for item in items:
                category = item.get("category", "uncategorized")
                groups.setdefault(category, []).append(item)

        return groups if groups else {"all": items}

    def _export_markdown(self, items: list[dict[str, Any]]) -> str:
        """Export items as markdown."""
        groups = self._group_items(items)
        lines: list[str] = []

        for group_name, group_items in groups.items():
            if len(groups) > 1:
                lines.append(f"## {group_name}")
                lines.append("")

            for item in group_items:
                title = item.get("title", "Untitled")
                url = item.get("url", "")
                content = item.get("content", "")
                tags = item.get("tags", [])
                date = item.get("published_date", "")

                # Title as heading
                lines.append(f"# {title}")

                # Link
                if url:
                    lines.append(f"[{title}]({url})")

                # Metadata
                if self.config.include_metadata and date:
                    lines.append(f"**Published:** {date}")

                # Tags
                if self.config.include_tags and tags:
                    tag_str = ", ".join(tags)
                    lines.append(f"**Tags:** {tag_str}")

                # Content/Summary
                if content:
                    lines.append("")
                    if self.config.include_summary:
                        summary = self._truncate(content, 200)
                        lines.append(summary)
                    else:
                        lines.append(content)

                lines.append("")

        return "\n".join(lines).strip()

    def _export_html(self, items: list[dict[str, Any]]) -> str:
        """Export items as HTML."""
        groups = self._group_items(items)
        lines: list[str] = []
        lines.append("<!DOCTYPE html>")
        lines.append("<html><head><meta charset=\"utf-8\"></head><body>")
        lines.append("<h1>Exported Content</h1>")

        for group_name, group_items in groups.items():
            if len(groups) > 1:
                lines.append(f"<h2>{html.escape(group_name)}</h2>")

            lines.append("<ul>")
            for item in group_items:
                title = html.escape(item.get("title", "Untitled"))
                url = html.escape(item.get("url", ""))
                content = html.escape(item.get("content", ""))
                tags = item.get("tags", [])
                date = item.get("published_date", "")

                lines.append("<li>")
                lines.append(f"<h3><a href=\"{url}\">{title}</a></h3>")

                if self.config.include_metadata and date:
                    lines.append(f"<p><em>Published: {html.escape(date)}</em></p>")

                if self.config.include_tags and tags:
                    tag_str = ", ".join(html.escape(t) for t in tags)
                    lines.append(f"<p>Tags: {tag_str}</p>")

                if content:
                    display = self._truncate(content, 200) if self.config.include_summary else content
                    lines.append(f"<p>{html.escape(display)}</p>")

                lines.append("</li>")
            lines.append("</ul>")

        lines.append("</body></html>")
        return "\n".join(lines)

    def _export_plain_text(self, items: list[dict[str, Any]]) -> str:
        """Export items as plain text."""
        groups = self._group_items(items)
        lines: list[str] = []

        for group_name, group_items in groups.items():
            if len(groups) > 1:
                lines.append(f"=== {group_name} ===")
                lines.append("")

            for item in group_items:
                title = item.get("title", "Untitled")
                url = item.get("url", "")
                content = item.get("content", "")
                tags = item.get("tags", [])
                date = item.get("published_date", "")

                lines.append(f"{title}")
                lines.append(f"{url}")

                if self.config.include_metadata and date:
                    lines.append(f"Date: {date}")

                if self.config.include_tags and tags:
                    lines.append(f"Tags: {', '.join(tags)}")

                if content:
                    display = self._truncate(content, 200) if self.config.include_summary else content
                    lines.append(display)

                lines.append("-" * 40)
                lines.append("")

        return "\n".join(lines).strip()

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max_length, adding ellipsis if needed."""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."
