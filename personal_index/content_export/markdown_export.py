"""Markdown export functionality for personal-index content.

Exports content items to formatted Markdown documents with
headings, links, tags, and metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MarkdownExporter:
    """Exports content data to Markdown format.

    Generates readable Markdown documents with proper formatting
    for content items, collections, and summaries.
    """

    def export_item(self, item: dict[str, Any]) -> str:
        """Export a single content item to Markdown."""
        lines = [f"## {item.get('title', 'Untitled')}", ""]
        url = item.get("url", "")
        if url:
            lines.extend([f"[{item.get('title', 'Untitled')}]({url})", ""])
        if item.get("description"):
            lines.extend([item["description"], ""])
        self._render_tags(item, lines)
        if item.get("bookmarked"):
            lines.extend(["*Bookmarked*", ""])
        if item.get("score") is not None:
            lines.extend([f"**Score:** {item['score']:.2f}", ""])
        self._render_metadata(item, lines)
        return "\n".join(lines)

    @staticmethod
    def _render_tags(item: dict[str, Any], lines: list[str]) -> None:
        """Render tags section to lines."""
        if not item.get("tags"):
            return
        tags = item["tags"]
        tag_str = ", ".join(f"`{t}`" for t in tags) if isinstance(tags, list) else str(tags)
        lines.extend([f"**Tags:** {tag_str}", ""])

    @staticmethod
    def _render_metadata(item: dict[str, Any], lines: list[str]) -> None:
        """Render metadata section to lines."""
        if not item.get("metadata"):
            return
        lines.extend(["### Metadata", ""])
        for key, value in item["metadata"].items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")

    def export_items(
        self,
        items: list[dict[str, Any]],
        title: str = "Content Export",
    ) -> str:
        """Export multiple items to a Markdown document.

        Args:
            items: List of content items.
            title: Document title.

        Returns:
            Complete Markdown document string.
        """
        lines = [f"# {title}", ""]
        lines.append(f"*Exported at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        for item in items:
            lines.append(self.export_item(item))
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
        title: str = "Content Export",
    ) -> int:
        """Export items to a Markdown file.

        Args:
            items: List of content items.
            filepath: Path to the output file.
            title: Document title.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items, title=title)
        filepath.write_text(content, encoding="utf-8")
        return len(items)

    def export_table(
        self,
        items: list[dict[str, Any]],
        columns: list[str] | None = None,
    ) -> str:
        """Export items as a Markdown table."""
        if not items:
            return ""
        if columns is None:
            columns = ["title", "url", "tags", "score", "bookmarked"]
        available = {k for item in items for k in item}
        columns = [c for c in columns if c in available]
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        for item in items:
            row = [self._format_value(item.get(col, "")) for col in columns]
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a cell value for markdown table."""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)
