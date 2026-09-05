"""Import bookmarks and content from various formats."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import ClassVar

from defusedxml.ElementTree import (
    ParseError as ET_ParseError,
)
from defusedxml.ElementTree import (
    fromstring as ET_fromstring,
)

from .bookmarks import Bookmark, BookmarkManager


@dataclass
class ImportResult:
    total_imported: int = 0
    total_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    source: str = ""
    format: str = ""
    imported_at: str = ""

    def __post_init__(self):
        if not self.imported_at:
            self.imported_at = datetime.now(timezone.utc).isoformat()


class Importer:
    """Import bookmarks from various file formats."""

    SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "csv", "html", "xml", "necko", "netscape"}

    def __init__(self, manager: BookmarkManager | None = None):
        self._manager = manager or BookmarkManager()

    @property
    def manager(self) -> BookmarkManager:
        """Manager."""
        return self._manager

    def import_from_file(self, filepath: str) -> ImportResult:
        """Import bookmarks from a file, auto-detecting format."""
        path = Path(filepath)
        if not path.exists():
            return ImportResult(errors=[f"File not found: {filepath}"], source=filepath)

        ext = path.suffix.lstrip(".").lower()
        if ext not in self.SUPPORTED_FORMATS:
            return ImportResult(
                errors=[f"Unsupported format: {ext}"],
                source=filepath,
                format=ext,
            )

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return self.import_from_content(content, ext, source=filepath)

    def import_from_content(self, content: str, fmt: str, source: str = "") -> ImportResult:
        """Import bookmarks from content string with specified format."""
        fmt = fmt.lower().lstrip(".")

        if fmt == "json":
            return self._import_json(content, source)
        if fmt == "csv":
            return self._import_csv(content, source)
        if fmt in ("html", "necko", "netscape"):
            return self._import_html(content, source)
        if fmt == "xml":
            return self._import_xml(content, source)
        return ImportResult(errors=[f"Unsupported format: {fmt}"], source=source, format=fmt)

    def _import_json(self, content: str, source: str = "") -> ImportResult:
        """Import bookmarks from a JSON document or array.

        Decodes ``content`` with :func:`json.loads`; on ``JSONDecodeError``
        appends ``"Invalid JSON: ..."`` to ``result.errors`` and returns
        early with zero items processed. A top-level JSON object (dict) is
        normalized to a single-element list so dict and array inputs are
        handled uniformly. For each item: if the resulting ``Bookmark.url``
        is non-empty the bookmark is written via ``self._manager.add`` and
        ``result.total_imported`` is incremented; if the url is empty the
        item is counted in ``result.total_skipped`` with no manager write.
        A per-item ``ValueError``/``TypeError`` (raised during ``Bookmark``
        construction or ``manager.add``) is caught, appended to
        ``result.errors`` as ``"Error importing item: ..."`` and the loop
        continues to the next item rather than aborting.
        """
        result = ImportResult(source=source, format="json")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON: {e}")
            return result

        if isinstance(data, dict):
            data = [data]

        for item in data:
            try:
                bookmark = Bookmark(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    category=item.get("category", "imported"),
                    tags=item.get("tags", []),
                    is_favorite=item.get("is_favorite", False),
                )
                if bookmark.url:
                    self._manager.add(bookmark)
                    result.total_imported += 1
                else:
                    result.total_skipped += 1
            except (ValueError, TypeError) as e:
                result.errors.append(f"Error importing item: {e}")

        return result

    def _import_csv(self, content: str, source: str = "") -> ImportResult:
        """Import bookmarks from CSV content.

        Iterates ``csv.DictReader`` rows over ``content`` and, per row,
        builds a ``Bookmark`` using case-insensitive header fallback
        (``url``/``URL``, ``title``/``Title``, ``description``/``Description``,
        ``category``/``Category`` defaulting to ``"imported"``, ``tags``/``Tags``
        comma-split and stripped, ``favorite``/``Favorite`` lowercased and
        compared to ``"true"``). Rows with a non-empty ``url`` are added to
        ``self._manager`` and counted in ``total_imported``; rows with an empty
        ``url`` are counted in ``total_skipped``. A per-row
        ``(ValueError, TypeError)`` is appended to ``result.errors`` and the
        loop continues. Returns the accumulated ``ImportResult``.
        """
        result = ImportResult(source=source, format="csv")
        reader = csv.DictReader(StringIO(content))

        for row in reader:
            try:
                bookmark = Bookmark(
                    url=row.get("url", row.get("URL", "")),
                    title=row.get("title", row.get("Title", "")),
                    description=row.get("description", row.get("Description", "")),
                    category=row.get("category", row.get("Category", "imported")),
                    tags=[t.strip() for t in row.get("tags", row.get("Tags", "")).split(",") if t.strip()],
                    is_favorite=row.get("favorite", row.get("Favorite", "false")).lower() == "true",
                )
                if bookmark.url:
                    self._manager.add(bookmark)
                    result.total_imported += 1
                else:
                    result.total_skipped += 1
            except (ValueError, TypeError) as e:
                result.errors.append(f"Error importing row: {e}")

        return result

    def _import_html(self, content: str, source: str = "") -> ImportResult:
        """Import from HTML bookmark format (Netscape/Neko)."""
        result = ImportResult(source=source, format="html")

        # Basic validation: content must look like HTML
        stripped = content.strip()
        if not stripped.startswith("<") or ">" not in stripped:
            result.errors.append("Invalid HTML: content does not appear to be HTML")
            return result

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
        except ImportError:
            try:
                tree = ET_fromstring(content)
            except ET_ParseError as e:
                result.errors.append(f"Invalid HTML/XML: {e}")
                return result
            self._parse_html_element(tree, result, [])
            return result

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            title = a_tag.get("title", a_tag.get_text(strip=True) or "")
            bookmark = Bookmark(
                url=str(href),
                title=str(title) if title else "",
                category="imported",
            )
            self._manager.add(bookmark)
            result.total_imported += 1

        return result

    def _parse_html_element(self, element, result: ImportResult, path: list[str]):
        """Recursively parse HTML bookmark elements (ElementTree fallback)."""
        tag = element.tag.lower()

        if tag == "a":
            href = element.get("href", "")
            title = element.get("title", element.text or "")
            if href:
                bookmark = Bookmark(
                    url=href,
                    title=title,
                    category="imported",
                )
                self._manager.add(bookmark)
                result.total_imported += 1

        for child in element:
            self._parse_html_element(child, result, path)

    def _import_xml(self, content: str, source: str = "") -> ImportResult:
        """Import from generic XML format."""
        result = ImportResult(source=source, format="xml")
        try:
            root = ET_fromstring(content)
        except ET_ParseError as e:
            result.errors.append(f"Invalid XML: {e}")
            return result

        for bookmark_elem in root.findall(".//bookmark"):
            try:
                url = bookmark_elem.get("url", bookmark_elem.findtext("url", ""))
                title = bookmark_elem.findtext("title", bookmark_elem.get("title", ""))
                description = bookmark_elem.findtext("description", "")
                category = bookmark_elem.findtext("category", "imported")
                tags_text = bookmark_elem.findtext("tags", "")
                tags = [t.strip() for t in tags_text.split(",") if t.strip()]

                bookmark = Bookmark(
                    url=url,
                    title=title,
                    description=description,
                    category=category,
                    tags=tags,
                )
                if bookmark.url:
                    self._manager.add(bookmark)
                    result.total_imported += 1
                else:
                    result.total_skipped += 1
            except (ValueError, TypeError) as e:
                result.errors.append(f"Error parsing bookmark element: {e}")

        return result

    def import_opml(self, content: str, source: str = "") -> ImportResult:
        """Import from OPML format."""
        result = ImportResult(source=source, format="opml")
        try:
            root = ET_fromstring(content)
        except ET_ParseError as e:
            result.errors.append(f"Invalid OPML: {e}")
            return result

        for outline in root.findall(".//outline[@text]"):
            url = outline.get("xmlUrl", outline.get("htmlUrl", ""))
            title = outline.get("title", outline.get("text", ""))
            if url:
                bookmark = Bookmark(url=url, title=title, category="imported")
                self._manager.add(bookmark)
                result.total_imported += 1

        return result

    """Result of an import operation."""

