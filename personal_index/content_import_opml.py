"""Content import OPML module - import OPML bookmarks."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Set


@dataclass
class OPMLBookmark:
    """A bookmark imported from OPML format."""

    url: str
    title: str = ""
    text: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    folder: str = ""
    outline_type: str = ""

    def __repr__(self) -> str:
        return f"OPMLBookmark(url={self.url!r}, title={self.title!r})"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "description": self.description,
            "tags": self.tags,
            "folder": self.folder,
            "outline_type": self.outline_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OPMLBookmark":
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            text=data.get("text", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            folder=data.get("folder", ""),
            outline_type=data.get("outline_type", ""),
        )


@dataclass
class OPMLImportResult:
    """Result of an OPML import operation."""

    total_imported: int = 0
    total_skipped: int = 0
    bookmarks: List[OPMLBookmark] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_title: str = ""

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "total_imported": self.total_imported,
            "total_skipped": self.total_skipped,
            "bookmarks": [b.to_dict() for b in self.bookmarks],
            "errors": self.errors,
            "source_title": self.source_title,
        }


class OPMLImporter:
    """Import bookmarks from OPML format."""

    def __init__(self, manager=None) -> None:
        self._manager = manager
        self._seen_urls: Set[str] = set()

    def import_opml(self, content: str, source: str = "") -> OPMLImportResult:
        """Import bookmarks from OPML content string."""
        result = OPMLImportResult()

        if not content or not content.strip():
            result.errors.append("Empty OPML content")
            return result

        # Parse XML
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            result.errors.append(f"Invalid OPML XML: {e}")
            return result

        # Validate OPML root
        if root.tag != "opml":
            result.errors.append("Not an OPML document: root element is not 'opml'")
            return result

        # Extract head metadata
        head = root.find("head")
        if head is not None:
            title_elem = head.find("title")
            if title_elem is not None and title_elem.text:
                result.source_title = title_elem.text.strip()

        # Extract source
        if not result.source_title and source:
            result.source_title = source

        # Find body
        body = root.find("body")
        if body is None:
            result.errors.append("OPML document has no body element")
            return result

        # Parse outlines recursively
        self._seen_urls.clear()
        self._parse_outlines(body, result, folder_path="")

        # Add to manager if provided
        if self._manager is not None:
            from personal_index.bookmarks import Bookmark
            for bm in result.bookmarks:
                bookmark = Bookmark(
                    url=bm.url,
                    title=bm.title,
                    description=bm.description,
                    category=bm.folder or "imported",
                    tags=bm.tags,
                )
                self._manager.add(bookmark)

        return result

    def _parse_outlines(
        self,
        element: ET.Element,
        result: OPMLImportResult,
        folder_path: str,
    ) -> None:
        """Recursively parse outline elements."""
        for outline in element:
            if outline.tag != "outline":
                continue

            text = outline.get("text", "")
            title = outline.get("title", text)
            xml_url = outline.get("xmlUrl", "")
            html_url = outline.get("htmlUrl", "")
            description = outline.get("description", "")
            outline_type = outline.get("type", "")
            tags_str = outline.get("_tags", "")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

            # Determine URL: prefer xmlUrl, fall back to htmlUrl
            url = xml_url or html_url

            # Check if this outline has children (folder)
            has_children = any(
                child.tag == "outline" for child in outline
            )

            if url and not has_children:
                # This is a bookmark entry
                if url in self._seen_urls:
                    result.total_skipped += 1
                    continue
                self._seen_urls.add(url)

                bookmark = OPMLBookmark(
                    url=url,
                    title=title,
                    text=text,
                    description=description,
                    tags=tags,
                    folder=folder_path,
                    outline_type=outline_type,
                )
                result.bookmarks.append(bookmark)
                result.total_imported += 1

            # Build folder path for children
            child_folder = folder_path
            if text:
                if folder_path:
                    child_folder = f"{folder_path}/{text}"
                else:
                    child_folder = text

            # Recurse into children
            if has_children:
                self._parse_outlines(outline, result, child_folder)
