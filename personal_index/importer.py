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
        """Import bookmarks from a file, dispatching on its extension.

        Args:
            filepath: path to the source file.

        Behavior:
            - Builds ``path = Path(filepath)``; if ``not path.exists()``
              returns ``ImportResult(errors=[f"File not found: {filepath}"],
              source=filepath)`` (no ``format`` set).
            - Derives ``ext = path.suffix.lstrip(".").lower()``; if
              ``ext not in self.SUPPORTED_FORMATS`` ({"json", "csv", "html",
              "xml", "necko", "netscape"}) returns
              ``ImportResult(errors=[f"Unsupported format: {ext}"],
              source=filepath, format=ext)``.
            - Otherwise opens the file (utf-8), reads its content, and
              delegates to ``self.import_from_content(content, ext,
              source=filepath)`` - returning that result unchanged.
            - No direct side effects on ``self._manager``; storage is
              handled by the delegated ``import_from_content``.
        """
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
        """Import bookmarks from a content string in the given format.

        Normalizes ``fmt`` via ``fmt.lower().lstrip(".")`` (so "JSON", ".csv",
        "Html" all match), then dispatches to the matching private helper:
        "json" -> ``_import_json``, "csv" -> ``_import_csv``, "html"/"necko"/
        "netscape" -> ``_import_html``, "xml" -> ``_import_xml``. On no match
        returns ``ImportResult(errors=[f"Unsupported format: {fmt}"],
        source=source, format=fmt)`` with total_imported/total_skipped at 0.
        Returns the helper's ImportResult (or the unsupported-format result);
        does not mutate self.
        """
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
        """Import bookmarks from an HTML bookmark file (Netscape/Neko).

        Validates that ``content.strip()`` starts with ``"<"`` and contains
        ``">"``; otherwise appends ``"Invalid HTML: content does not appear to
        be HTML"`` to ``result.errors`` and returns early. Parses ``content``
        with ``BeautifulSoup(content, "html.parser")``; on ``ImportError``
        falls back to ``ET_fromstring`` + ``_parse_html_element`` (appending
        ``"Invalid HTML/XML: ..."`` to ``result.errors`` on ``ET_ParseError``
        and returning early). With BeautifulSoup, iterates
        ``soup.find_all("a", href=True)`` and, per anchor, builds a
        ``Bookmark`` from ``href`` (url), the ``title`` attribute or
        ``get_text(strip=True)`` (title) and ``category="imported"``; adds it
        to ``self._manager`` and increments ``result.total_imported``. Returns
        the accumulated ``ImportResult`` (``format="html"``).
        """
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
        """Recursively walk the ElementTree fallback tree, importing
        ``<a>`` anchors into ``self._manager``.

        Reads ``element.tag`` (lowercased). Only when it equals ``"a"``
        does it read the ``href`` attribute (default ``""``) and the
        ``title`` attribute (falling back to ``element.text`` or ``""``);
        a ``Bookmark`` (``url=href``, ``title=title``,
        ``category="imported"``) is added to ``self._manager`` and
        ``result.total_imported`` incremented ONLY when ``href`` is
        truthy - an ``<a>`` with no ``href`` is silently skipped (no
        ``total_skipped`` increment, no error). Every child element is
        then recursed into via ``self._parse_html_element(child, result,
        path)``. The ``path`` parameter is accepted but never used. The
        method returns ``None``; it mutates ``result`` and
        ``self._manager`` in place.
        """
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
        """Import bookmarks from a generic XML document.

        Parses ``content`` with ``ET_fromstring``; on ``ET_ParseError``
        appends "Invalid XML: ..." to ``result.errors`` and returns the
        result early. Otherwise iterates ``root.findall(".//bookmark")`` and
        for each element extracts url (attribute or ``<url>`` child), title,
        description, category (default "imported") and tags (comma-split,
        whitespace-stripped, empties dropped). A ``Bookmark`` is added to
        ``self._manager`` and ``result.total_imported`` incremented when its
        url is truthy; otherwise ``result.total_skipped`` is incremented.
        Per-element ``ValueError``/``TypeError`` are caught and appended to
        ``result.errors``. Returns an ``ImportResult`` with ``format="xml"``.
        """
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
        """Parse OPML content via ET_fromstring and import bookmarks into self._manager.

        On ET_ParseError, appends "Invalid OPML: {e}" to result.errors and
        returns early. Iterates root.findall(".//outline[@text]") (only
        outlines with a text attribute). For each outline: url is taken from
        the xmlUrl attribute (falling back to htmlUrl, then empty string);
        title is taken from the title attribute (falling back to the text
        attribute, then empty string). When url is truthy, a Bookmark(url,
        title, category="imported") is added to self._manager and
        result.total_imported is incremented. When url is falsy, no bookmark
        is created and no counter is incremented. Returns
        ImportResult(source=source, format="opml").
        """
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

