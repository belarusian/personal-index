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

        # Also handle top-level links not in dl
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href not in self._seen_urls:
                self._seen_urls.add(href)
                title = a.get_text(strip=True) or a.get("title", "")
                bm = HTMLBookmark(url=href, title=title)
                result.bookmarks.append(bm)
                result.total_imported += 1

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
        dl: "BeautifulSoup",  # noqa: F821
        result: HTMLImportResult,
        folder_path: str,
    ) -> None:
        """Process a <dl> element and its children."""
        current_folder = folder_path
        pending_link: Optional[HTMLBookmark] = None

        for child in dl.children:
            if child.name == "dt":
                # Check for <h3> folder header
                h3 = child.find("h3", recursive=False)
                if h3:
                    folder_name = h3.get_text(strip=True)
                    if folder_path:
                        current_folder = f"{folder_path}/{folder_name}"
                    else:
                        current_folder = folder_name
                    pending_link = None
                    continue

                # Check for <a> link
                a_tag = child.find("a", href=True, recursive=False)
                if a_tag:
                    href = a_tag["href"]
                    if href in self._seen_urls:
                        result.total_skipped += 1
                        pending_link = None
                        continue
                    self._seen_urls.add(href)

                    title = a_tag.get_text(strip=True) or a_tag.get("title", "")
                    description = ""
                    tags = []
                    add_date = a_tag.get("add_date", "")
                    last_modified = a_tag.get("last_modified", "")
                    icon = a_tag.get("icon", "")

                    # Parse tags attribute
                    tags_str = a_tag.get("tags", "")
                    if tags_str:
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                    # Filter out data: icons
                    if icon and icon.startswith("data:"):
                        icon = ""

                    pending_link = HTMLBookmark(
                        url=href,
                        title=title,
                        description=description,
                        tags=tags,
                        folder=current_folder,
                        add_date=add_date,
                        last_modified=last_modified,
                        icon=icon,
                    )
                    continue

                # <hr> separator - just skip
                pending_link = None

            elif child.name == "dd":
                # Description follows a <dt> link
                if pending_link:
                    desc_text = child.get_text(strip=True)
                    if desc_text:
                        if pending_link.description:
                            pending_link.description += " " + desc_text
                        else:
                            pending_link.description = desc_text

            elif child.name == "dl":
                # Nested list - process recursively
                self._process_dl(child, result, current_folder)
                pending_link = None

            elif child.name == "p":
                # <p> is just a separator in Netscape format
                pass

            # Finalize pending link
            if pending_link:
                result.bookmarks.append(pending_link)
                result.total_imported += 1
                pending_link = None
