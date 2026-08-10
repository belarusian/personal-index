"""Export content as markdown, HTML, or plain text."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExportFormat(Enum):
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
    group_by: str | None = None

    def __post_init__(self) -> None:
        if self.sort_by not in ("date", "title", "priority"):
            raise ValueError(
                f"Invalid sort_by value: {self.sort_by!r}. "
                "Must be one of: 'date', 'title', 'priority'."
            )
        if self.group_by is not None and self.group_by not in ("tags", "date"):
            raise ValueError(
                f"Invalid group_by value: {self.group_by!r}. "
                "Must be one of: 'tags', 'date' or None."
            )


class MarkdownExporter:
    """Export content items as markdown, HTML, or plain text."""

    def __init__(self, config: ExportConfig | None = None) -> None:
        self.config = config or ExportConfig()

    def export(
        self,
        items: list[dict[str, Any]],
        format: ExportFormat = ExportFormat.MARKDOWN,
    ) -> str:
        """Export a list of content items.

        Args:
            items: List of content item dicts with keys like
                   'url', 'title', 'content', 'tags', 'published_date',
                   'priority_score'.
            format: The export format (markdown, html, plain_text).

        Returns:
            The exported content as a string.
        """
        if not items:
            return ""

        sorted_items = self._sort_items(items)

        if self.config.group_by:
            grouped = self._group_items(sorted_items)
            return self._render_grouped(grouped, format)

        return self._render_items(sorted_items, format)

    def _sort_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort items according to config."""
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
        return items

    def _group_items(
        self, items: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group items by the configured group_by field."""
        grouped: dict[str, list[dict[str, Any]]] = {}
        if self.config.group_by == "tags":
            for item in items:
                tags = item.get("tags", [])
                if tags:
                    for tag in tags:
                        if tag not in grouped:
                            grouped[tag] = []
                        grouped[tag].append(item)
                else:
                    key = "untagged"
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(item)
        elif self.config.group_by == "date":
            for item in items:
                date = item.get("published_date", "unknown")
                if date:
                    # Group by month
                    key = date[:7] if len(date) >= 7 else date
                else:
                    key = "unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(item)
        return grouped

    def _render_grouped(
        self,
        grouped: dict[str, list[dict[str, Any]]],
        format: ExportFormat,
    ) -> str:
        """Render grouped items."""
        parts: list[str] = []
        for group_key, group_items in grouped.items():
            if format == ExportFormat.MARKDOWN:
                parts.append(f"\n## {group_key}\n")
            elif format == ExportFormat.HTML:
                parts.append(f"<h2>{html.escape(str(group_key))}</h2>\n")
            else:
                parts.append(f"\n== {group_key} ==\n")
            parts.append(self._render_items(group_items, format))
        return "\n".join(parts)

    def _render_items(
        self, items: list[dict[str, Any]], format: ExportFormat
    ) -> str:
        """Render a list of items in the given format."""
        parts: list[str] = []
        for item in items:
            if format == ExportFormat.MARKDOWN:
                parts.append(self._render_markdown_item(item))
            elif format == ExportFormat.HTML:
                parts.append(self._render_html_item(item))
            else:
                parts.append(self._render_plain_text_item(item))
        return "\n".join(parts)

    def _render_markdown_item(self, item: dict[str, Any]) -> str:
        """Render a single item as markdown."""
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        content = item.get("content", "")
        tags = item.get("tags", [])
        published_date = item.get("published_date", "")

        lines: list[str] = []

        # Title as heading
        lines.append(f"## {title}")

        # Link
        if url:
            lines.append(f"[{title}]({url})")

        # Metadata
        if self.config.include_metadata and published_date:
            lines.append(f"**Published:** {published_date}")

        # Tags
        if self.config.include_tags and tags:
            lines.append(f"**Tags:** {', '.join(tags)}")

        # Content
        if content:
            lines.append("")
            if self.config.include_summary:
                summary = self._summarize(content)
                lines.append(summary)
            else:
                lines.append(content)

        return "\n".join(lines)

    def _render_html_item(self, item: dict[str, Any]) -> str:
        """Render a single item as HTML."""
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        content = item.get("content", "")
        tags = item.get("tags", [])
        published_date = item.get("published_date", "")

        parts: list[str] = []

        # Title as heading
        escaped_title = html.escape(title)
        parts.append(f"<h2>{escaped_title}</h2>")

        # Link
        if url:
            escaped_url = html.escape(url)
            parts.append(f'<p><a href="{escaped_url}">{escaped_title}</a></p>')

        # Metadata
        if self.config.include_metadata and published_date:
            parts.append(f"<p><strong>Published:</strong> {html.escape(published_date)}</p>")

        # Tags
        if self.config.include_tags and tags:
            escaped_tags = ", ".join(html.escape(t) for t in tags)
            parts.append(f"<p><strong>Tags:</strong> {escaped_tags}</p>")

        # Content
        if content:
            escaped_content = html.escape(content)
            if self.config.include_summary:
                summary = self._summarize(content)
                escaped_summary = html.escape(summary)
                parts.append(f"<p>{escaped_summary}</p>")
            else:
                parts.append(f"<p>{escaped_content}</p>")

        return "\n".join(parts)

    def _render_plain_text_item(self, item: dict[str, Any]) -> str:
        """Render a single item as plain text."""
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        content = item.get("content", "")
        tags = item.get("tags", [])
        published_date = item.get("published_date", "")

        lines: list[str] = []

        lines.append(title)
        lines.append("-" * len(title))

        if url:
            lines.append(url)

        if self.config.include_metadata and published_date:
            lines.append(f"Published: {published_date}")

        if self.config.include_tags and tags:
            lines.append(f"Tags: {', '.join(tags)}")

        if content:
            lines.append("")
            if self.config.include_summary:
                lines.append(self._summarize(content))
            else:
                lines.append(content)

        return "\n".join(lines)

    def _summarize(self, text: str, max_length: int = 200) -> str:
        """Create a simple summary by truncating text."""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."
