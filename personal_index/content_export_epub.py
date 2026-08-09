"""Content EPUB export for personal-index.

Exports saved content as EPUB 3.0 ebooks with configurable layout.
EPUB files are ZIP archives containing XHTML chapters, a navigation
document, and a content.opf manifest.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EPUBChapterFormat(str, Enum):
    """Supported chapter content formats for EPUB export."""

    HTML = "html"
    TEXT = "text"


@dataclass
class EPUBExportConfig:
    """Configuration for EPUB export."""

    title: str = "Content Export"
    author: str = "personal-index"
    language: str = "en"
    include_cover: bool = True
    include_toc: bool = True
    chapter_format: EPUBChapterFormat = EPUBChapterFormat.HTML

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "language": self.language,
            "include_cover": self.include_cover,
            "include_toc": self.include_toc,
            "chapter_format": self.chapter_format.value,
        }


@dataclass
class EPUBContentItem:
    """A content item formatted for EPUB export."""

    url: str
    title: str
    content: str = ""
    word_count: int = 0
    category: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    def format_as_html(self) -> str:
        """Format item as an XHTML chapter for EPUB inclusion."""
        escaped_title = html.escape(self.title)
        escaped_content = html.escape(self.content)
        escaped_url = html.escape(self.url)

        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<html xmlns="http://www.w3.org/1999/xhtml">',
            "<head>",
            f"<title>{escaped_title}</title>",
            "</head>",
            "<body>",
            f"<h1>{escaped_title}</h1>",
        ]

        if self.url:
            parts.append(f'<p><a href="{escaped_url}">{escaped_url}</a></p>')

        if self.created_at:
            parts.append(f'<p class="meta">Saved: {html.escape(self.created_at)}</p>')

        if self.category:
            parts.append(f'<p class="meta">Category: {html.escape(self.category)}</p>')

        if self.tags:
            escaped_tags = ", ".join(html.escape(t) for t in self.tags)
            parts.append(f'<p class="meta">Tags: {escaped_tags}</p>')

        if self.word_count:
            parts.append(f'<p class="meta">Word count: {self.word_count}</p>')

        parts.append("<hr/>")
        parts.append(f"<p>{escaped_content}</p>")
        parts.append("</body>")
        parts.append("</html>")

        return "\n".join(parts)

    def format_as_text(self) -> str:
        """Format item as plain text for EPUB inclusion."""
        lines = [f"# {self.title}", ""]
        if self.url:
            lines.append(f"URL: {self.url}")
        if self.created_at:
            lines.append(f"Saved: {self.created_at}")
        if self.category:
            lines.append(f"Category: {self.category}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        if self.word_count:
            lines.append(f"Word count: {self.word_count}")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)


@dataclass
class EPUBExportResult:
    """Result of an EPUB export operation."""

    success: bool = True
    items_exported: int = 0
    output: Optional[bytes] = None
    errors: list[str] = field(default_factory=list)
    exported_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "items_exported": self.items_exported,
            "exported_at": self.exported_at,
            "errors": self.errors,
        }


class EPUBExporter:
    """Exports content items as EPUB 3.0 ebooks.

    Produces a valid EPUB 3.0 file as bytes, containing:
    - mimetype (uncompressed, first entry)
    - META-INF/container.xml
    - content.opf (package document with manifest, spine, metadata)
    - nav.xhtml (navigation document / table of contents)
    - chapter_N.xhtml (one per content item)
    - cover.xhtml (optional cover page)
    """

    def __init__(self, config: Optional[EPUBExportConfig] = None) -> None:
        self.config = config or EPUBExportConfig()

    def _generate_mimetype(self) -> bytes:
        """Generate the mimetype file content."""
        return b"application/epub+zip"

    def _generate_container_xml(self) -> str:
        """Generate META-INF/container.xml."""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            "  <rootfiles>\n"
            '    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>\n'
            "  </rootfiles>\n"
            "</container>\n"
        )

    def _generate_cover_xhtml(self) -> str:
        """Generate a simple cover page."""
        escaped_title = html.escape(self.config.title)
        escaped_author = html.escape(self.config.author)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head>\n"
            "  <title>Cover</title>\n"
            "</head>\n"
            "<body>\n"
            '  <div style="text-align:center; padding-top: 4em;">\n'
            f"    <h1>{escaped_title}</h1>\n"
            f"    <p>{escaped_author}</p>\n"
            f"    <p>{now}</p>\n"
            "  </div>\n"
            "</body>\n"
            "</html>\n"
        )

    def _generate_nav_xhtml(
        self, items: list[EPUBContentItem]
    ) -> str:
        """Generate the navigation document (nav.xhtml)."""
        escaped_title = html.escape(self.config.title)
        nav_items = []
        for i, item in enumerate(items, 1):
            chapter_id = f"chapter_{i}"
            escaped_chapter_title = html.escape(item.title)
            nav_items.append(
                f'        <li><a href="{chapter_id}.xhtml">'
                f"{escaped_chapter_title}</a></li>"
            )
        nav_list = "\n".join(nav_items)

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head>\n"
            f"  <title>{escaped_title}</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <nav epub:type='toc' id='toc'>\n"
            f"    <h1>{escaped_title}</h1>\n"
            "    <ol>\n"
            f"{nav_list}\n"
            "    </ol>\n"
            "  </nav>\n"
            "</body>\n"
            "</html>\n"
        )

    def _generate_content_opf(
        self, items: list[EPUBContentItem]
    ) -> str:
        """Generate the package document (content.opf)."""
        escaped_title = html.escape(self.config.title)
        escaped_author = html.escape(self.config.author)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build manifest entries
        manifest_entries = []
        spine_entries = []

        # Nav is included in manifest/spine only when include_toc is True
        if self.config.include_toc:
            manifest_entries.append(
                '    <item id="nav" href="nav.xhtml" '
                'media-type="application/xhtml+xml" '
                "properties='nav'/>"
            )
            spine_entries.append('    <itemref idref="nav"/>')

        # Cover
        if self.config.include_cover:
            manifest_entries.append(
                '    <item id="cover" href="cover.xhtml" '
                'media-type="application/xhtml+xml"/>'
            )
            spine_entries.append('    <itemref idref="cover"/>')

        # Chapters
        for i, item in enumerate(items, 1):
            chapter_id = f"chapter_{i}"
            manifest_entries.append(
                f'    <item id="{chapter_id}" href="{chapter_id}.xhtml" '
                'media-type="application/xhtml+xml"/>'
            )
            spine_entries.append(f'    <itemref idref="{chapter_id}"/>')

        manifest_block = "\n".join(manifest_entries)
        spine_block = "\n".join(spine_entries)

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<package version="3.0" xmlns="http://www.idpf.org/2007/opf" '
            'unique-identifier="uid">\n'
            "  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n"
            f'    <dc:identifier id="uid">urn:uuid:{self._generate_uuid()}</dc:identifier>\n'
            f"    <dc:title>{escaped_title}</dc:title>\n"
            f"    <dc:creator>{escaped_author}</dc:creator>\n"
            f"    <dc:language>{self.config.language}</dc:language>\n"
            f"    <dc:date>{now}</dc:date>\n"
            "    <meta property='dcterms:modified'>{now}</meta>\n"
            "  </metadata>\n"
            "  <manifest>\n"
            f"{manifest_block}\n"
            "  </manifest>\n"
            "  <spine>\n"
            f"{spine_block}\n"
            "  </spine>\n"
            "</package>\n"
        )

    def _generate_uuid(self) -> str:
        """Generate a simple UUID for the EPUB package."""
        seed = f"{self.config.title}-{self.config.author}-{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]

    def _write_chapter(
        self, zf: zipfile.ZipFile, item: EPUBContentItem, index: int
    ) -> None:
        """Write a single chapter file to the ZIP."""
        chapter_id = f"chapter_{index}"
        if self.config.chapter_format == EPUBChapterFormat.HTML:
            content = item.format_as_html()
        else:
            content = item.format_as_text()
        zf.writestr(f"{chapter_id}.xhtml", content.encode("utf-8"))

    def export(self, items: list[EPUBContentItem]) -> EPUBExportResult:
        """Export items to an EPUB 3.0 ebook as bytes.

        Args:
            items: List of EPUBContentItem objects to export.

        Returns:
            EPUBExportResult with the EPUB bytes in the output field.
        """
        try:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # mimetype must be first and uncompressed
                zf.writestr(
                    "mimetype",
                    self._generate_mimetype(),
                    compress_type=zipfile.ZIP_STORED,
                )

                # Container
                zf.writestr(
                    "META-INF/container.xml",
                    self._generate_container_xml().encode("utf-8"),
                )

                # Cover page
                if self.config.include_cover:
                    zf.writestr(
                        "cover.xhtml",
                        self._generate_cover_xhtml().encode("utf-8"),
                    )

                # Navigation document (always included for valid EPUB)
                zf.writestr(
                    "nav.xhtml",
                    self._generate_nav_xhtml(items).encode("utf-8"),
                )

                # Chapters
                for i, item in enumerate(items, 1):
                    self._write_chapter(zf, item, i)

                # Package document
                zf.writestr(
                    "content.opf",
                    self._generate_content_opf(items).encode("utf-8"),
                )

            return EPUBExportResult(
                success=True,
                items_exported=len(items),
                output=buffer.getvalue(),
            )

        except Exception as e:
            return EPUBExportResult(
                success=False,
                items_exported=0,
                errors=[str(e)],
            )

    def export_from_dicts(self, items: list[dict]) -> EPUBExportResult:
        """Export items from raw dictionaries.

        Each dict should have at minimum 'url' and 'title' keys.
        Optional keys: content, word_count, category, tags, created_at.

        Args:
            items: List of content item dictionaries.

        Returns:
            EPUBExportResult with the EPUB bytes in the output field.
        """
        epub_items = []
        for item in items:
            epub_items.append(
                EPUBContentItem(
                    url=item.get("url", ""),
                    title=item.get("title", "Untitled"),
                    content=item.get("content", ""),
                    word_count=item.get("word_count", 0),
                    category=item.get("category", ""),
                    tags=item.get("tags", []),
                    created_at=item.get("created_at"),
                )
            )
        return self.export(epub_items)
