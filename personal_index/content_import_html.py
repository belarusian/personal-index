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

        Netscape HTML bookmarks use <dl>/<dt>/<dd>/<h3> structure.
        BeautifulSoup nests <dt> elements inside each other and wraps
        them in <p> tags, so we need to handle this carefully.
        """
        current_folder = folder_path

        # Get all direct children of the dl element
        children = list(dl.children)

        i = 0
        while i < len(children):
            child = children[i]

            # Skip whitespace text nodes and <p> separators
            if child.name is None or child.name == "p":
                # But check if <p> contains meaningful children
                if child.name == "p":
                    p_children = list(child.children)
                    # Process children of <p> as if they were direct children
                    for p_child in p_children:
                        if p_child.name == "dt":
                            self._process_dt(p_child, result, current_folder)
                        elif p_child.name == "dl":
                            self._process_dl(p_child, result, current_folder)
                        elif p_child.name == "h3":
                            folder_name = p_child.get_text(strip=True)
                            if folder_name:
                                if folder_path:
                                    current_folder = f"{folder_path}/{folder_name}"
                                else:
                                    current_folder = folder_name
                i += 1
                continue

            if child.name == "h3":
                # Folder header
                folder_name = child.get_text(strip=True)
                if folder_name:
                    if folder_path:
                        current_folder = f"{folder_path}/{folder_name}"
                    else:
                        current_folder = folder_name
                i += 1
                continue

            if child.name == "dt":
                self._process_dt(child, result, current_folder)
                i += 1
                continue

            if child.name == "dl":
                # Nested dl
                self._process_dl(child, result, current_folder)
                i += 1
                continue

            if child.name == "hr":
                i += 1
                continue

            i += 1

    def _process_dt(self, dt, result: HTMLImportResult, folder_path: str) -> None:
        """Process a <dt> element which may contain a link or nested content."""
        # Check for <a> link
        a_tag = dt.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if href in self._seen_urls:
                result.total_skipped += 1
                return
            self._seen_urls.add(href)

            title = a_tag.get_text(strip=True) or a_tag.get("title", "")
            tags_str = a_tag.get("tags", "")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
            add_date = a_tag.get("add_date", "")
            last_modified = a_tag.get("last_modified", "")
            icon = a_tag.get("icon", "")

            # Filter out data: icons
            if icon and icon.startswith("data:"):
                icon = ""

            # Look for <dd> description
            description = ""
            dd = dt.find("dd")
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

        # Check for nested <dl> (folder with sub-items)
        nested_dl = dt.find("dl")
        if nested_dl:
            self._process_dl(nested_dl, result, folder_path)

        # Check for nested <h3> (folder header inside dt)
        h3 = dt.find("h3")
        if h3:
            folder_name = h3.get_text(strip=True)
            if folder_name:
                new_folder = f"{folder_path}/{folder_name}" if folder_path else folder_name
                # Look for dl after h3 within this dt
                nested_dl = dt.find("dl")
                if nested_dl:
                    self._process_dl(nested_dl, result, new_folder)
