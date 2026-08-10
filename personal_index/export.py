from __future__ import annotations

"""Export bookmarks and indexed content to various formats."""


import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import ClassVar

from .bookmarks import BookmarkManager

# Map file extensions to format names

EXTENSION_MAP = {
    "json": "json",
    "csv": "csv",
    "html": "html",
    "htm": "html",
    "xml": "xml",
    "md": "markdown",
    "markdown": "markdown",
    "opml": "opml",
}


@dataclass
class ExportResult:
    """Result of an export operation."""
    total_exported: int = 0
    output_path: str = ""
    format: str = ""
    exported_at: str = ""
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()


class Exporter:
    """Export bookmarks to various file formats."""

    SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "csv", "html", "xml", "markdown", "opml"}

    def __init__(self, manager: BookmarkManager | None = None):
        self._manager = manager or BookmarkManager()

    @property
    def manager(self) -> BookmarkManager:
        """Manager."""
        return self._manager

    def export_to_file(self, filepath: str, fmt: str | None = None) -> ExportResult:
        """Export bookmarks to a file, auto-detecting format from extension."""
        if fmt is None:
            ext = Path(filepath).suffix.lstrip(".").lower()
            fmt = EXTENSION_MAP.get(ext)
            if fmt is None:
                return ExportResult(errors=[f"Unsupported format: {ext}"])

        content = self.export_to_content(fmt)
        if content is None:
            return ExportResult(errors=[f"Export failed for format: {fmt}"])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return ExportResult(
            total_exported=self._manager.count(),
            output_path=filepath,
            format=fmt,
        )

    def export_to_content(self, fmt: str) -> str | None:
        """Export bookmarks to a string in the specified format."""
        fmt = fmt.lower()
        if fmt == "json":
            return self._export_json()
        if fmt == "csv":
            return self._export_csv()
        if fmt == "html":
            return self._export_html()
        if fmt == "xml":
            return self._export_xml()
        if fmt == "markdown":
            return self._export_markdown()
        if fmt == "opml":
            return self._export_opml()
        return None

    def _export_json(self) -> str:
        """Export as JSON."""
        bookmarks = [b.to_dict() for b in self._manager.list_all()]
        return json.dumps(bookmarks, indent=2, ensure_ascii=False)

    def _export_csv(self) -> str:
        """Export as CSV."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["url", "title", "description", "category", "tags", "is_favorite", "created_at", "updated_at"])
        for b in self._manager.list_all():
            writer.writerow([
                b.url,
                b.title,
                b.description,
                b.category,
                ";".join(b.tags),
                b.is_favorite,
                b.created_at,
                b.updated_at,
            ])
        return output.getvalue()

    def _export_html(self) -> str:
        """Export as Netscape HTML bookmark format."""
        lines = [
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            f'<TITLE>Bookmarks exported at {datetime.now(timezone.utc).isoformat()}</TITLE>',
            '<H1>Bookmarks</H1>',
            '<DL><p>',
        ]

        for b in self._manager.list_all():
            lines.append(
                f'<DT><A HREF="{b.url}" ADD_DATE="0">{self._escape_html(b.title or b.url)}</A>'
            )

        lines.extend(["</DL><p>", "</DL>"])
        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _export_xml(self) -> str:
        """Export as XML."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<bookmarks>"]
        for b in self._manager.list_all():
            tags_str = ",".join(b.tags)
            lines.append(
                f'  <bookmark url="{self._escape_xml(b.url)}">'
                f'<title>{self._escape_xml(b.title)}</title>'
                f'<description>{self._escape_xml(b.description)}</description>'
                f'<category>{self._escape_xml(b.category)}</category>'
                f'<tags>{self._escape_xml(tags_str)}</tags>'
                f'<is_favorite>{b.is_favorite}</is_favorite>'
                f'<created_at>{b.created_at}</created_at>'
                f'<updated_at>{b.updated_at}</updated_at>'
                f"</bookmark>"
            )
        lines.append("</bookmarks>")
        return "\n".join(lines)

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _export_markdown(self) -> str:
        """Export as Markdown."""
        lines = ["# Bookmarks", ""]

        categories = self._manager.get_categories()
        for category in categories:
            lines.append(f"## {category}")
            lines.append("")
            bookmarks = self._manager.list_by_category(category)
            for b in bookmarks:
                fav_marker = " ⭐" if b.is_favorite else ""
                title = b.title or b.url
                lines.append(f"- [{title}]({b.url}){fav_marker}")
                if b.description:
                    lines.append(f"  - {b.description}")
                if b.tags:
                    lines.append(f"  - Tags: {', '.join(b.tags)}")
            lines.append("")

        return "\n".join(lines)

    def _export_opml(self) -> str:
        """Export as OPML format."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<opml version="2.0">',
            "<body>",
        ]
        for b in self._manager.list_all():
            lines.append(
                f'  <outline text="{self._escape_xml(b.title or b.url)}" '
                f'htmlUrl="{b.url}" type="bookmark"/>'
            )
        lines.extend(["</body>", "</opml>"])
        return "\n".join(lines)

    def export_filtered(
        self,
        fmt: str,
        category: str | None = None,
        tag: str | None = None,
        favorites_only: bool = False,
    ) -> str | None:
        """Export filtered bookmarks to a string."""
        bookmarks = self._manager.list_all()

        if category:
            bookmarks = [b for b in bookmarks if b.category == category]
        if tag:
            bookmarks = [b for b in bookmarks if tag in b.tags]
        if favorites_only:
            bookmarks = [b for b in bookmarks if b.is_favorite]

        # Temporarily replace manager's bookmarks for export
        original = self._manager._bookmarks
        self._manager._bookmarks = {b.url: b for b in bookmarks}
        content = self.export_to_content(fmt)
        self._manager._bookmarks = original
        return content
