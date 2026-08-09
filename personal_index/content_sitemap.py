"""Content sitemap - generate sitemap of saved content."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class SitemapFormat(str, Enum):
    """Output format for sitemap."""
    XML = "xml"
    TEXT = "text"
    JSON = "json"


@dataclass
class SitemapEntry:
    """A single entry in a sitemap."""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: str = "monthly"
    priority: float = 0.5

    def to_xml(self) -> str:
        """Convert entry to XML string."""
        url_elem = ET.Element("url")

        loc_elem = ET.SubElement(url_elem, "loc")
        loc_elem.text = self.url

        if self.lastmod is not None:
            lastmod_elem = ET.SubElement(url_elem, "lastmod")
            lastmod_elem.text = self.lastmod.strftime("%Y-%m-%d")

        changefreq_elem = ET.SubElement(url_elem, "changefreq")
        changefreq_elem.text = self.changefreq

        priority_elem = ET.SubElement(url_elem, "priority")
        priority_elem.text = str(self.priority)

        return ET.tostring(url_elem, encoding="unicode")


@dataclass
class SitemapIndexEntry:
    """An entry in a sitemap index."""
    sitemap_url: str
    lastmod: Optional[datetime] = None

    def to_xml(self) -> str:
        """Convert index entry to XML string."""
        sitemap_elem = ET.Element("sitemap")

        loc_elem = ET.SubElement(sitemap_elem, "loc")
        loc_elem.text = self.sitemap_url

        if self.lastmod is not None:
            lastmod_elem = ET.SubElement(sitemap_elem, "lastmod")
            lastmod_elem.text = self.lastmod.strftime("%Y-%m-%d")

        return ET.tostring(sitemap_elem, encoding="unicode")


@dataclass
class SitemapDocument:
    """A complete sitemap document."""
    entries: list[SitemapEntry] = field(default_factory=list)

    def add_entry(self, entry: SitemapEntry) -> None:
        """Add an entry to the document."""
        self.entries.append(entry)

    def to_xml(self) -> str:
        """Generate XML sitemap document."""
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = ET.Element("urlset", {
            "xmlns": ns,
        })

        for entry in self.entries:
            url_elem = ET.Element("url")

            loc_elem = ET.SubElement(url_elem, "loc")
            loc_elem.text = entry.url

            if entry.lastmod is not None:
                lastmod_elem = ET.SubElement(url_elem, "lastmod")
                lastmod_elem.text = entry.lastmod.strftime("%Y-%m-%d")

            changefreq_elem = ET.SubElement(url_elem, "changefreq")
            changefreq_elem.text = entry.changefreq

            priority_elem = ET.SubElement(url_elem, "priority")
            priority_elem.text = str(entry.priority)

            root.append(url_elem)

        # Force non-self-closing tag for empty urlset
        xml_str = ET.tostring(root, encoding="unicode")
        if xml_str.endswith(" />"):
            xml_str = xml_str[:-3] + "></urlset>"

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    @property
    def entry_count(self) -> int:
        return len(self.entries)


class SitemapGenerator:
    """Generates sitemaps from saved content."""

    VALID_CHANGEFREQUENCIES = {
        "always", "hourly", "daily", "weekly", "monthly", "yearly", "never",
    }

    def __init__(self, max_entries_per_sitemap: int = 50000):
        self.max_entries_per_sitemap = max_entries_per_sitemap
        self._entries: list[SitemapEntry] = []
        self._seen_urls: set[str] = set()

    def add_url(
        self,
        url: str,
        title: str = "",
        lastmod: Optional[datetime] = None,
        changefreq: str = "monthly",
        priority: float = 0.5,
    ) -> None:
        """Add a URL to the sitemap."""
        if url in self._seen_urls:
            return

        # Clamp priority to valid range [0.0, 1.0]
        priority = max(0.0, min(1.0, priority))

        # Validate changefreq
        if changefreq not in self.VALID_CHANGEFREQUENCIES:
            changefreq = "monthly"

        entry = SitemapEntry(
            url=url,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
        )
        self._entries.append(entry)
        self._seen_urls.add(url)

    def bulk_add_urls(
        self,
        urls: list[tuple[str, str]],
        changefreq: str = "monthly",
        priority: float = 0.5,
    ) -> None:
        """Add multiple URLs at once. Each tuple is (url, title)."""
        for url, title in urls:
            self.add_url(url, title=title, changefreq=changefreq, priority=priority)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._seen_urls.clear()

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def generate(self, fmt: SitemapFormat = SitemapFormat.XML) -> str:
        """Generate sitemap in the specified format."""
        if fmt == SitemapFormat.XML:
            return self._generate_xml()
        elif fmt == SitemapFormat.TEXT:
            return self._generate_text()
        elif fmt == SitemapFormat.JSON:
            return self._generate_json()
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _generate_xml(self) -> str:
        """Generate XML sitemap."""
        doc = SitemapDocument(entries=list(self._entries))
        return doc.to_xml()

    def _generate_text(self) -> str:
        """Generate plain text sitemap (one URL per line)."""
        lines = [entry.url for entry in self._entries]
        return "\n".join(lines)

    def _generate_json(self) -> str:
        """Generate JSON sitemap."""
        urls = []
        for entry in self._entries:
            url_data = {
                "loc": entry.url,
                "changefreq": entry.changefreq,
                "priority": entry.priority,
            }
            if entry.lastmod is not None:
                url_data["lastmod"] = entry.lastmod.isoformat()
            urls.append(url_data)

        data = {
            "urls": urls,
            "total": len(urls),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(data, indent=2)

    def generate_index(
        self,
        base_url: str,
        sitemap_prefix: str = "sitemap",
    ) -> str:
        """Generate a sitemap index XML."""
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = ET.Element("sitemapindex", {"xmlns": ns})

        # Split entries into chunks if needed
        chunks = []
        for i in range(0, len(self._entries), self.max_entries_per_sitemap):
            chunks.append(self._entries[i:i + self.max_entries_per_sitemap])

        now = datetime.now(timezone.utc)
        for idx, chunk in enumerate(chunks):
            sitemap_url = f"{base_url}/{sitemap_prefix}-{idx + 1}.xml"
            index_entry = SitemapIndexEntry(
                sitemap_url=sitemap_url,
                lastmod=now,
            )
            root.append(ET.fromstring(index_entry.to_xml()))

        xml_str = ET.tostring(root, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
