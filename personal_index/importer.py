"""Import bookmarks and content from various formats."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from .bookmarks import Bookmark, BookmarkManager


@dataclass
class ImportResult:
    """Result of an import operation."""
    total_imported: int = 0
    total_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    source: str = ""
    format: str = ""
    imported_at: str = ""

    def __post_init__(self):
        if not self.imported_at:
            self.imported_at = datetime.now(timezone.utc).isoformat()


class Importer:
    """Import bookmarks from various file formats."""

    SUPPORTED_FORMATS = {"json", "csv", "html", "xml", "necko", "netscape"}

    def __init__(self, manager: Optional[BookmarkManager] = None):
        self._manager = manager or BookmarkManager()

    @property
    def manager(self) -> BookmarkManager:
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
        elif fmt == "csv":
            return self._import_csv(content, source)
        elif fmt in ("html", "necko", "netscape"):
            return self._import_html(content, source)
        elif fmt == "xml":
            return self._import_xml(content, source)
        else:
            return ImportResult(errors=[f"Unsupported format: {fmt}"], source=source, format=fmt)

    def _import_json(self, content: str, source: str = "") -> ImportResult:
        """Import from JSON format."""
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
            except Exception as e:
                result.errors.append(f"Error importing item: {e}")

        return result

    def _import_csv(self, content: str, source: str = "") -> ImportResult:
        """Import from CSV format."""
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
            except Exception as e:
                result.errors.append(f"Error importing row: {e}")

        return result

    def _import_html(self, content: str, source: str = "") -> ImportResult:
        """Import from HTML bookmark format (Netscape/Neko)."""
        result = ImportResult(source=source, format="html")
        try:
            tree = ET.fromstring(content)
        except ET.ParseError as e:
            result.errors.append(f"Invalid HTML/XML: {e}")
            return result

        self._parse_html_element(tree, result, [])

        return result

    def _parse_html_element(self, element, result: ImportResult, path: List[str]):
        """Recursively parse HTML bookmark elements."""
        tag = element.tag.lower()

        if tag == "a":
            href = element.get("href", "")
            title = element.get("add_date", element.get("icon", element.text or ""))
            # Try to get title from attributes
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
            root = ET.fromstring(content)
        except ET.ParseError as e:
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
            except Exception as e:
                result.errors.append(f"Error parsing bookmark element: {e}")

        return result

    def import_opml(self, content: str, source: str = "") -> ImportResult:
        """Import from OPML format."""
        result = ImportResult(source=source, format="opml")
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
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
