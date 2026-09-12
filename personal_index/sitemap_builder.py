"""Sitemap XML generator for indexed URLs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

logger = logging.getLogger(__name__)

# Sitemap namespace
SM_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NSMAP = {"": SM_NS}
register_namespace("", SM_NS)

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
        """Build the <url> Element for this entry.

        Creates a <url> Element and attaches exactly four SubElements:
        loc (text = self.url), lastmod (text = self.last_modified formatted
        as "%Y-%m-%dT%H:%M:%SZ"), changefreq (text = self.change_frequency),
        and priority (text = self.priority formatted to one decimal place).
        Returns the <url> Element.
        """
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
        """Append a new SitemapEntry to the builder.

        Constructs a SitemapEntry from the four arguments (url, last_modified,
        change_frequency, priority) and appends it to self.entries. When
        last_modified is None the entry auto-fills it with the current UTC
        time; priority is clamped to [0.0, 1.0]. Returns None.
        """
        self.entries.append(SitemapEntry(url, last_modified, change_frequency, priority))

    def add_entries(self, entries: list[SitemapEntry]) -> None:
        """Extend the builder's entries in place.

        Extends self.entries with the passed entries list in order (no copy or
        de-duplication). Returns None.
        """
        self.entries.extend(entries)

    @staticmethod
    def _qualify(elem: Element) -> Element:
        """Return a copy of elem with every tag qualified by SM_NS.

        Recursively rewrites the tag of elem and all of its descendants to
        ``{SM_NS}<localname>`` (preserving text, tail and attributes) so the
        serialized document carries the sitemap namespace on every element.
        Because SM_NS is registered as the default namespace, the serialized
        bytes still use bare local names (no prefix) while a parser that
        looks up the namespace recovers the qualified tags.
        """
        local = elem.tag.split("}")[-1]
        new = Element(f"{{{SM_NS}}}{local}")
        new.text = elem.text
        new.tail = elem.tail
        for attr, value in elem.attrib.items():
            new.set(attr, value)
        for child in elem:
            new.append(SitemapBuilder._qualify(child))
        return new

    def build(self) -> bytes:
        """Build the complete sitemap XML as bytes.

        Serializes every entry in self.entries unconditionally into a single
        <urlset> document. Enforces NO size limit: it does not cap the URL
        count (MAX_URLS_PER_SITEMAP) nor the serialized byte size
        (MAX_SITEMAP_SIZE_BYTES). A caller who needs to respect either limit
        must split first - split_into_chunks() for the URL-count limit or
        split_by_size() for the byte-size limit - and build() each chunk
        separately.
        """
        root = Element(f"{{{SM_NS}}}urlset")
        for entry in self.entries:
            root.append(self._qualify(entry.to_element()))
        xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'.encode()

    def build_sitemap_index(self, sitemap_urls: list[str]) -> bytes:
        """Build a sitemap index file referencing multiple sitemaps."""
        root = Element(f"{{{SM_NS}}}sitemapindex")
        for url in sitemap_urls:
            sitemap_elem = SubElement(root, f"{{{SM_NS}}}sitemap")
            SubElement(sitemap_elem, f"{{{SM_NS}}}loc").text = url
        xml_str = tostring(root, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'.encode()

    def split_into_chunks(self, chunk_size: int = MAX_URLS_PER_SITEMAP) -> list[list[SitemapEntry]]:
        """Split entries into chunks of at most chunk_size URLs each.

        Splits by URL count only: [self.entries[i:i+chunk_size] for i in
        range(0, len(self.entries), chunk_size)]. Enforces the URL-count
        limit (MAX_URLS_PER_SITEMAP is the default chunk_size) but NOT the
        serialized byte-size limit (MAX_SITEMAP_SIZE_BYTES) - a chunk can
        still serialize to more than 50 MB if its URLs carry long loc/lastmod
        values. Use split_by_size() to enforce the byte budget. Guard path:
        chunk_size <= 0 raises ValueError from range().
        """
        chunks = []
        for i in range(0, len(self.entries), chunk_size):
            chunks.append(self.entries[i : i + chunk_size])
        return chunks

    def split_by_size(self, max_bytes: int = MAX_SITEMAP_SIZE_BYTES) -> list[list[SitemapEntry]]:
        """Split entries into chunks that each serialize to at most max_bytes.

        Measures each entry's serialized length (len(tostring(entry.to_element(),
        encoding="unicode"))) and breaks a chunk when adding the next entry
        would push the chunk's serialized size past max_bytes. The fixed
        per-chunk wrapper overhead (the XML declaration + <urlset> root that
        build() emits) is measured once via a single build() call and added to
        each chunk's running total, so a chunk returned here serializes to at
        most max_bytes bytes when passed to build(). Unlike split_into_chunks
        (URL count only), this enforces the MAX_SITEMAP_SIZE_BYTES byte budget.
        A single entry whose own serialized size exceeds max_bytes still gets
        its own chunk (it cannot be split further). An empty builder returns
        an empty list.
        """
        if not self.entries:
            return []
        # Measure the fixed per-chunk wrapper overhead once (build() of a
        # single-entry builder minus that entry's own serialized length), so
        # the running total matches exactly what build() would emit.
        probe = SitemapBuilder(self.domain)
        probe.add_entries([self.entries[0]])
        overhead = len(probe.build()) - len(tostring(self.entries[0].to_element(), encoding="unicode"))
        chunks: list[list[SitemapEntry]] = []
        current: list[SitemapEntry] = []
        current_bytes = overhead
        for entry in self.entries:
            entry_bytes = len(tostring(entry.to_element(), encoding="unicode"))
            if current and current_bytes + entry_bytes > max_bytes:
                chunks.append(current)
                current = []
                current_bytes = overhead
            current.append(entry)
            current_bytes += entry_bytes
        if current:
            chunks.append(current)
        return chunks

    def clear(self) -> None:
        """Empty the builder's entries list in place.

        Calls self.entries.clear(), removing every SitemapEntry currently
        held. Returns None.
        """
        self.entries.clear()

    @property
    def url_count(self) -> int:
        """Return the number of entries currently held by the builder.

        Returns len(self.entries) - the count of SitemapEntry objects in the
        builder's entries list.
        """
        return len(self.entries)
