from __future__ import annotations

from typing import ClassVar

"""Sitemap parser for discovering URLs on websites."""


import xml.etree.ElementTree as ET
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin


@dataclass
class SitemapEntry:
    """A single entry from a sitemap."""
    loc: str
    lastmod: str | None = None
    changefreq: str = "monthly"
    priority: float = 0.5

    def is_valid(self) -> bool:
        """Check if the entry has a valid location."""
        return bool(self.loc and self.loc.startswith(("http://", "https://")))


@dataclass
class Sitemap:
    """Parsed sitemap data."""
    entries: list[SitemapEntry] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)  # nested sitemap URLs
    source_url: str = ""

    @property
    def url_count(self) -> int:
        """Number of URLs in this sitemap."""
        return len(self.entries)

    @property
    def sitemap_count(self) -> int:
        """Number of nested sitemaps."""
        return len(self.sitemaps)

    def get_urls(self) -> list[str]:
        """Get all URLs from entries."""
        return [e.loc for e in self.entries if e.is_valid()]


class SitemapParser:
    """Parse XML sitemaps and sitemap indexes."""

    NAMESPACES: ClassVar[dict[str, str]] = {
        "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }

    def parse(self, xml_content: str, source_url: str = "") -> Sitemap:
        """Parse sitemap XML content."""
        if not xml_content:
            return Sitemap(source_url=source_url)

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return Sitemap(source_url=source_url)

        sitemap = Sitemap(source_url=source_url)

        # Check if this is a sitemap index (root tag is sitemapindex)
        root_tag = root.tag
        # Strip namespace if present
        if "}" in root_tag:
            root_tag = root_tag.split("}", 1)[1]

        if root_tag == "sitemapindex":
            # Try with namespace first
            for sitemap_elem in root.findall("ns:sitemap", self.NAMESPACES):
                loc_elem = sitemap_elem.find("ns:loc", self.NAMESPACES)
                if loc_elem is not None and loc_elem.text:
                    loc = loc_elem.text.strip()
                    if source_url and not loc.startswith(("http://", "https://")):
                        loc = urljoin(source_url, loc)
                    sitemap.sitemaps.append(loc)
            # Also try without namespace
            if not sitemap.sitemaps:
                for sitemap_elem in root.findall("sitemap"):
                    loc_elem = sitemap_elem.find("loc")
                    if loc_elem is not None and loc_elem.text:
                        loc = loc_elem.text.strip()
                        if source_url and not loc.startswith(("http://", "https://")):
                            loc = urljoin(source_url, loc)
                        sitemap.sitemaps.append(loc)
            return sitemap

        # Also check for nested sitemapindex element
        sitemap_index = root.find("ns:sitemapindex", self.NAMESPACES)
        if sitemap_index is not None:
            for sitemap_elem in sitemap_index.findall("ns:sitemap", self.NAMESPACES):
                loc_elem = sitemap_elem.find("ns:loc", self.NAMESPACES)
                if loc_elem is not None and loc_elem.text:
                    loc = loc_elem.text.strip()
                    if source_url and not loc.startswith(("http://", "https://")):
                        loc = urljoin(source_url, loc)
                    sitemap.sitemaps.append(loc)
            return sitemap

        # Parse regular sitemap entries
        for url_elem in root.findall("ns:url", self.NAMESPACES):
            entry = self._parse_url_element(url_elem, source_url)
            if entry:
                sitemap.entries.append(entry)

        return sitemap

    def _parse_url_element(
        self, url_elem: ET.Element, base_url: str = ""
    ) -> SitemapEntry | None:
        """Parse a single <url> element."""
        loc_elem = url_elem.find("ns:loc", self.NAMESPACES)
        if loc_elem is None or not loc_elem.text:
            return None

        loc = loc_elem.text.strip()
        if base_url and not loc.startswith(("http://", "https://")):
            loc = urljoin(base_url, loc)

        lastmod_elem = url_elem.find("ns:lastmod", self.NAMESPACES)
        lastmod = lastmod_elem.text.strip() if lastmod_elem is not None and lastmod_elem.text else None

        changefreq_elem = url_elem.find("ns:changefreq", self.NAMESPACES)
        changefreq = changefreq_elem.text.strip() if changefreq_elem is not None and changefreq_elem.text else "monthly"

        priority_elem = url_elem.find("ns:priority", self.NAMESPACES)
        priority = 0.5
        if priority_elem is not None and priority_elem.text:
            with suppress(ValueError):
                priority = float(priority_elem.text.strip())

        return SitemapEntry(
            loc=loc,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
        )

    def parse_text_sitemap(self, text: str, base_url: str = "") -> Sitemap:
        """Parse a plain text sitemap (one URL per line)."""
        sitemap = Sitemap(source_url=base_url)
        if not text:
            return sitemap

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if base_url and not line.startswith(("http://", "https://")):
                line = urljoin(base_url, line)
            entry = SitemapEntry(loc=line)
            if entry.is_valid():
                sitemap.entries.append(entry)

        return sitemap

    def filter_by_priority(self, sitemap: Sitemap, min_priority: float = 0.5) -> list[SitemapEntry]:
        """Filter sitemap entries by minimum priority."""
        return [e for e in sitemap.entries if e.priority >= min_priority]

    def filter_by_changefreq(
        self, sitemap: Sitemap, freq: str = "daily"
    ) -> list[SitemapEntry]:
        """Filter sitemap entries by change frequency."""
        return [e for e in sitemap.entries if e.changefreq == freq]

    def get_recent_entries(
        self, sitemap: Sitemap, days: int = 30
    ) -> list[SitemapEntry]:
        """Get entries modified within the last N days."""
        cutoff = datetime.now(timezone.utc)
        entries = []
        for entry in sitemap.entries:
            if entry.lastmod:
                try:
                    lastmod = datetime.fromisoformat(entry.lastmod.replace("Z", "+00:00"))
                    if (cutoff - lastmod).days <= days:
                        entries.append(entry)
                except (ValueError, TypeError):
                    pass
        return entries
