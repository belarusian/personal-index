"""Sitemap XML generator for indexed URLs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)

# Sitemap namespace
SM_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NSMAP = {"": SM_NS}


class SitemapEntry:
    """Represents a single URL entry in a sitemap."""

    def __init__(
        self,
        url: str,
        last_modified: datetime | None = None,
        change_frequency: str = "monthly",
        priority: float = 0.5,
    ):
        self.url = url
        self.last_modified = last_modified or datetime.now(timezone.utc)
        self.change_frequency = change_frequency
        self.priority = max(0.0, min(1.0, priority))

    def to_element(self) -> Element:
        """To_element."""
        url_elem = Element("url")
        SubElement(url_elem, "loc").text = self.url
        SubElement(url_elem, "lastmod").text = self.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
        SubElement(url_elem, "changefreq").text = self.change_frequency
        SubElement(url_elem, "priority").text = f"{self.priority:.1f}"
        return url_elem


class SitemapBuilder:
    """Builds XML sitemap from a collection of URLs."""

    MAX_URLS_PER_SITEMAP = 50_000
    MAX_SITEMAP_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

    def __init__(self, domain: str = ""):
        self.domain = domain
        self.entries: list[SitemapEntry] = []

    def add_entry(
        self,
        url: str,
        last_modified: datetime | None = None,
        change_frequency: str = "monthly",
        priority: float = 0.5,
    ) -> None:
        """Process add_entry.

        Args:
            url, last_modified, change_frequency, priority.
        """
        self.entries.append(SitemapEntry(url, last_modified, change_frequency, priority))

    def add_entries(self, entries: list[SitemapEntry]) -> None:
        """Process add_entries.

        Args:
        entries.
        """
        self.entries.extend(entries)

    def build(self) -> bytes:
        """Build the complete sitemap XML as bytes."""
        root = Element("urlset", nsmap=NSMAP if NSMAP else {})
        for entry in self.entries:
            root.append(entry.to_element())
        xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'.encode("utf-8")

    def build_sitemap_index(self, sitemap_urls: list[str]) -> bytes:
        """Build a sitemap index file referencing multiple sitemaps."""
        root = Element("sitemapindex", nsmap=NSMAP if NSMAP else {})
        for url in sitemap_urls:
            sitemap_elem = SubElement(root, "sitemap")
            SubElement(sitemap_elem, "loc").text = url
        xml_str = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'.encode("utf-8")

    def split_into_chunks(self, chunk_size: int = MAX_URLS_PER_SITEMAP) -> list[list[SitemapEntry]]:
        """Split entries into chunks for multiple sitemap files."""
        chunks = []
        for i in range(0, len(self.entries), chunk_size):
            chunks.append(self.entries[i : i + chunk_size])
        return chunks

    def clear(self) -> None:
        """Clear."""
        self.entries.clear()

    @property
    def url_count(self) -> int:
        """Url_count."""
        return len(self.entries)
