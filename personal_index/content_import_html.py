"""Content import HTML module - import Netscape HTML bookmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


@dataclass
class HTMLBookmark:
    """A bookmark imported from Netscape HTML format."""

    url: str
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    folder: str = ""
    add_date: str = ""
    last_modified: str = ""
    icon: str = ""

    def __repr__(self) -> str:
        return f"HTMLBookmark(url={self.url!r}, title={self.title!r})"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "folder": self.folder,
            "add_date": self.add_date,
            "last_modified": self.last_modified,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HTMLBookmark":
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            folder=data.get("folder", ""),
            add_date=data.get("add_date", ""),
            last_modified=data.get("last_modified", ""),
            icon=data.get("icon", ""),
        )


@dataclass
class HTMLImportResult:
    """Result of an HTML bookmark import operation."""

    total_imported: int = 0
    total_skipped: int = 0
    bookmarks: List[HTMLBookmark] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "total_imported": self.total_imported,
            "total_skipped": self.total_skipped,
            "bookmarks": [b.to_dict() for b in self.bookmarks],
            "errors": self.errors,
        }


class HTMLImporter:
    """Import bookmarks from Netscape HTML bookmark format."""

    def __init__(self, manager=None) -> None:
        self._manager = manager
        self._seen_urls: Set[str] = set()

    def import_html(self, content: str, source: str = "") -> HTMLImportResult:
        """Import bookmarks from Netscape HTML content string."""
        result = HTMLImportResult()

        if not content or not content.strip():
            result.errors.append("Empty HTML content")
            return result

        if not _HAS_BS4:
            result.errors.append("beautifulsoup4 is required for HTML import")
            return result

        try:
            soup = BeautifulSoup(content, "html.parser")
        except Exception as e:
            result.errors.append(f"Failed to parse HTML: {e}")
            return result

        self._seen_urls.clear()

        # Process all <dl> elements
        for dl in soup.find_all("dl"):
            self._process_dl(dl, result, folder_path="")

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

    def _process_dl(
        self,
        dl,
        result: HTMLImportResult,
        folder_path: str,
    ) -> None:
        """Process a <dl> element and its children recursively.

        BeautifulSoup nests <dt> elements inside each other when parsing
        Netscape HTML. We need to recursively walk the tree to find all
        <a> tags and <h3> folder headers.
        """
        current_folder = folder_path

        # Walk all children of dl
        for child in dl.children:
            if child.name is None:
                # Whitespace text node
                continue
            elif child.name == "p":
                # <p> wraps dt elements - process its children
                for p_child in child.children:
                    self._process_element(p_child, result, current_folder)
            elif child.name == "h3":
                folder_name = child.get_text(strip=True)
                if folder_name:
                    if folder_path:
                        current_folder = f"{folder_path}/{folder_name}"
                    else:
                        current_folder = folder_name
            elif child.name == "dt":
                self._process_element(child, result, current_folder)
            elif child.name == "dl":
                self._process_dl(child, result, current_folder)
            elif child.name == "hr":
                pass  # separator, skip

    def _process_element(self, element, result: HTMLImportResult, folder_path: str) -> None:
        """Process a single element (dt, h3, etc.) and its children."""
        if element.name == "h3":
            folder_name = element.get_text(strip=True)
            if folder_name:
                if folder_path:
                    folder_path = f"{folder_path}/{folder_name}"
                else:
                    folder_path = folder_name

        if element.name == "dt":
            # Check for <a> link in this dt
            a_tag = element.find("a", href=True)
            if a_tag:
                href = a_tag["href"]
                if href in self._seen_urls:
                    result.total_skipped += 1
                else:
                    self._seen_urls.add(href)

                    title = a_tag.get_text(strip=True) or a_tag.get("title", "")
                    tags_str = a_tag.get("tags", "")
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                    add_date = a_tag.get("add_date", "")
                    last_modified = a_tag.get("last_modified", "")
                    icon = a_tag.get("icon", "")

                    if icon and icon.startswith("data:"):
                        icon = ""

                    # Look for <dd> description
                    description = ""
                    dd = element.find("dd")
                    if dd:
                        description = dd.get_text(strip=True)

                    bm = HTMLBookmark(
                        url=href,
                        title=title,
                        description=description,
                        tags=tags,
                        folder=folder_path,
                        add_date=add_date,
                        last_modified=last_modified,
                        icon=icon,
                    )
                    result.bookmarks.append(bm)
                    result.total_imported += 1

            # Recursively process children of this dt
            # (BeautifulSoup nests subsequent <dt> elements inside previous ones)
            for child in element.children:
                if child.name is None:
                    continue
                elif child.name in ("a", "dd", "hr", "p"):
                    # Skip elements we've already handled
                    continue
                elif child.name == "dt":
                    # Nested dt - process it at the same folder level
                    self._process_element(child, result, folder_path)
                elif child.name == "h3":
                    self._process_element(child, result, folder_path)
                elif child.name == "dl":
                    self._process_dl(child, result, folder_path)

        elif element.name == "dl":
            self._process_dl(element, result, folder_path)
