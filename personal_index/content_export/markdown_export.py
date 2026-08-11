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
        """Export a single content item to Markdown.

        Args:
            item: Content item dictionary.

        Returns:
            Markdown string for the item.
        """
        lines = []
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        lines.append(f"## {title}")
        lines.append("")

        if url:
            lines.append(f"[{title}]({url})")
            lines.append("")

        if item.get("description"):
            lines.append(item["description"])
            lines.append("")

        if item.get("tags"):
            tags = item["tags"]
            if isinstance(tags, list):
                tag_str = ", ".join(f"`{t}`" for t in tags)
            else:
                tag_str = str(tags)
            lines.append(f"**Tags:** {tag_str}")
            lines.append("")

        if item.get("bookmarked"):
            lines.append("*Bookmarked*")
            lines.append("")

        if item.get("score") is not None:
            lines.append(f"**Score:** {item['score']:.2f}")
            lines.append("")

        if item.get("metadata"):
            lines.append("### Metadata")
            lines.append("")
            for key, value in item["metadata"].items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\n".join(lines)

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
        """Export items as a Markdown table.

        Args:
            items: List of content items.
            columns: Columns to include (None for common ones).

        Returns:
            Markdown table string.
        """
        if not items:
            return ""

        if columns is None:
            columns = ["title", "url", "tags", "score", "bookmarked"]

        # Filter to available columns
        available: set[str] = set()
        for item in items:
            available.update(item.keys())
        columns = [c for c in columns if c in available]

        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"

        lines = [header, separator]

        for item in items:
            row_parts = []
            for col in columns:
                value = item.get(col, "")
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                elif isinstance(value, float):
                    value = f"{value:.2f}"
                row_parts.append(str(value))
            lines.append("| " + " | ".join(row_parts) + " |")

        return "\n".join(lines)
