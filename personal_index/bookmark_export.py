from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

"""Bookmark export module for exporting saved bookmarks as HTML, JSON, and OPML."""

@dataclass
class BookmarkExportResult:
    """Result of a bookmark export operation."""
    format: str = ""
    bookmark_count: int = 0
    output_path: str = ""
    exported_at: str = ""
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()


# Map file extensions to format names
_EXTENSION_MAP = {
    "json": "json",
    "html": "html",
    "htm": "html",
    "opml": "opml",
}


class BookmarkExporter:
    """Export bookmarks to HTML, JSON, and OPML formats.

    Accepts a list of Bookmark objects and provides methods to export them
    in three standard formats:
    - **JSON**: Pretty-printed array of bookmark dictionaries.
    - **HTML**: Netscape bookmark file format (importable by browsers).
    - **OPML**: OPML 2.0 outline format (used by feed readers and bookmark tools).
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "html", "opml"}

    def __init__(self, bookmarks: list):
        self.bookmarks = bookmarks

    # ------------------------------------------------------------------
    # JSON Export
    # ------------------------------------------------------------------

    def export_json(self) -> str:
        """Export bookmarks as a pretty-printed JSON string.

        Returns a JSON array where each element is a bookmark dictionary
        containing url, title, description, category, tags, is_favorite,
        created_at, and updated_at fields.
        """
        data = [b.to_dict() for b in self.bookmarks]
        return json.dumps(data, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # HTML Export
    # ------------------------------------------------------------------

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def export_html(self) -> str:
        """Export bookmarks as Netscape HTML bookmark format.

        Produces a standard Netscape bookmark file that can be imported
        into most browsers (Chrome, Firefox, Safari, Edge).
        """
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        lines = [
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Bookmarks</TITLE>",
            "<H1>Bookmarks</H1>",
            "<DL><p>",
        ]

        for b in self.bookmarks:
            display_title = self._escape_html(b.title if b.title else b.url)
            lines.append(
                f'<DT><A HREF="{b.url}" ADD_DATE="{now}">{display_title}</A>'
            )

        lines.extend(["</DL><p>", "</DL>"])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # OPML Export
    # ------------------------------------------------------------------

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters for OPML output."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def export_opml(self) -> str:
        """Export bookmarks as OPML 2.0 format.

        Produces a valid OPML 2.0 document with a head section containing
        metadata and a body section containing outline elements for each
        bookmark.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<opml version="2.0">',
            "<head>",
            "<title>Bookmarks</title>",
            f"<dateCreated>{now}</dateCreated>",
            f"<dateModified>{now}</dateModified>",
            "</head>",
            "<body>",
        ]

        for b in self.bookmarks:
            display_title = self._escape_xml(b.title if b.title else b.url)
            lines.append(
                f'  <outline text="{display_title}" '
                f'htmlUrl="{b.url}" type="bookmark"/>'
            )

        lines.extend(["</body>", "</opml>"])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Dispatch & File I/O
    # ------------------------------------------------------------------

    def export(self, fmt: str) -> str | None:
        """Export bookmarks in the specified format.

        Args:
            fmt: One of 'json', 'html', or 'opml' (case-insensitive).

        Returns:
            The exported content as a string, or None for unsupported formats.
        """
        fmt = fmt.lower()
        if fmt == "json":
            return self.export_json()
        if fmt == "html":
            return self.export_html()
        if fmt == "opml":
            return self.export_opml()
        return None

    def export_to_file(
        self, filepath: str, fmt: str | None = None
    ) -> BookmarkExportResult | None:
        """Export bookmarks to a file.

        Args:
            filepath: Destination file path. Format is auto-detected from
                      extension if *fmt* is not provided.
            fmt: Explicit format override ('json', 'html', 'opml').

        Returns:
            A BookmarkExportResult on success, or a result with errors on failure.
        """
        # Determine format
        if fmt is None:
            ext = Path(filepath).suffix.lstrip(".").lower()
            fmt = _EXTENSION_MAP.get(ext)

        if fmt is None or fmt not in self.SUPPORTED_FORMATS:
            return BookmarkExportResult(
                errors=[f"Unsupported format: {fmt}"]
            )

        # Generate content
        content = self.export(fmt)
        if content is None:
            return BookmarkExportResult(
                errors=[f"Export failed for format: {fmt}"]
            )

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return BookmarkExportResult(
            format=fmt,
            bookmark_count=len(self.bookmarks),
            output_path=filepath,
        )
