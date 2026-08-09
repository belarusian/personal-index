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

        # Find all <dl> elements and process them
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
        """Process a <dl> element and its children recursively."""
        current_folder = folder_path

        # Get direct children of dl
        children = list(dl.children)

        i = 0
        while i < len(children):
            child = children[i]

            # Skip NavigableString (whitespace) and <p> separators
            if child.name is None or child.name == "p":
                i += 1
                continue

            if child.name == "h3" or (child.name == "dt" and child.find("h3")):
                # Folder header
                if child.name == "h3":
                    folder_name = child.get_text(strip=True)
                else:
                    h3 = child.find("h3")
                    folder_name = h3.get_text(strip=True) if h3 else ""

                if folder_name:
                    if folder_path:
                        current_folder = f"{folder_path}/{folder_name}"
                    else:
                        current_folder = folder_name

                # Look for nested <dl> after this header
                next_child = children[i + 1] if i + 1 < len(children) else None
                if next_child and next_child.name == "dl":
                    self._process_dl(next_child, result, current_folder)

                i += 1
                continue

            if child.name == "dl":
                # Nested dl at same level (shouldn't normally happen but handle it)
                self._process_dl(child, result, current_folder)
                i += 1
                continue

            if child.name == "dt":
                # Check for <a> link inside <dt>
                a_tag = child.find("a", href=True)
                if a_tag:
                    href = a_tag["href"]
                    if href in self._seen_urls:
                        result.total_skipped += 1
                        i += 1
                        continue
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

                    # Look for <dd> description - it may be inside <dt> or as next sibling
                    description = ""

                    # Check for dd inside dt (BeautifulSoup nests dd inside dt)
                    dd_inside = child.find("dd")
                    if dd_inside:
                        description = dd_inside.get_text(strip=True)

                    # Also check next siblings for dd
                    j = i + 1
                    while j < len(children):
                        next_c = children[j]
                        if next_c.name == "dd":
                            desc_text = next_c.get_text(strip=True)
                            if desc_text:
                                if description:
                                    description += " " + desc_text
                                else:
                                    description = desc_text
                            j += 1
                        elif next_c.name == "dt":
                            break
                        elif next_c.name == "dl":
                            break
                        elif next_c.name == "hr":
                            break
                        else:
                            j += 1

                    bm = HTMLBookmark(
                        url=href,
                        title=title,
                        description=description,
                        tags=tags,
                        folder=current_folder,
                        add_date=add_date,
                        last_modified=last_modified,
                        icon=icon,
                    )
                    result.bookmarks.append(bm)
                    result.total_imported += 1

                # Check for nested dl inside dt (folder with links)
                nested_dl = child.find("dl")
                if nested_dl:
                    self._process_dl(nested_dl, result, current_folder)

                i += 1
                continue

            if child.name == "hr":
                i += 1
                continue

            i += 1
