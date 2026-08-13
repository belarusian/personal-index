"""RSS feed reader for personal index."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element as ET_Element

from defusedxml.ElementTree import ParseError as ET_ParseError
from defusedxml.ElementTree import fromstring as ET_fromstring


@dataclass
class FeedEntry:
    """A single entry from an RSS/Atom feed."""
    title: str = ""
    link: str = ""
    summary: str = ""
    content: str = ""
    author: str = ""
    published: str | None = None
    updated: str | None = None
    categories: list[str] = field(default_factory=list)
    guid: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "link": self.link,
            "summary": self.summary,
            "content": self.content,
            "author": self.author,
            "published": self.published,
            "updated": self.updated,
            "categories": self.categories,
            "guid": self.guid,
        }


@dataclass
class Feed:
    """A parsed RSS/Atom feed."""
    title: str = ""
    link: str = ""
    description: str = ""
    author: str = ""
    entries: list[FeedEntry] = field(default_factory=list)
    feed_url: str = ""

    @property
    def entry_count(self) -> int:
        """Number of entries in this feed."""
        return len(self.entries)

    def get_recent_entries(self, count: int = 10) -> list[FeedEntry]:
        """Get the most recent entries."""
        return self.entries[:count]


class RSSParser:
    """Parse RSS 2.0 and Atom feeds."""

    ATOM_NS = "http://www.w3.org/2005/Atom"

    def parse(self, xml_content: str, feed_url: str = "") -> Feed:
        """Parse RSS or Atom feed XML content."""
        if not xml_content:
            return Feed(feed_url=feed_url)

        try:
            root = ET_fromstring(xml_content)
        except ET_ParseError:
            return Feed(feed_url=feed_url)

        root_tag = root.tag
        if "}" in root_tag:
            root_tag = root_tag.split("}", 1)[1]

        feed = Feed(feed_url=feed_url)

        if root_tag == "rss":
            feed = self._parse_rss(root, feed_url)
        elif root_tag == "feed":
            feed = self._parse_atom(root, feed_url)

        feed.feed_url = feed_url
        return feed

    def _parse_rss(self, root: ET_Element, feed_url: str) -> Feed:
        """Parse RSS 2.0 feed."""
        feed = Feed(feed_url=feed_url)
        channel = root.find("channel")
        if channel is None:
            return feed

        title_elem = channel.find("title")
        feed.title = title_elem.text if title_elem is not None and title_elem.text else ""

        link_elem = channel.find("link")
        feed.link = link_elem.text if link_elem is not None and link_elem.text else ""

        desc_elem = channel.find("description")
        feed.description = desc_elem.text if desc_elem is not None and desc_elem.text else ""

        author_elem = channel.find("managingEditor")
        if author_elem is None:
            author_elem = channel.find("author")
        feed.author = author_elem.text if author_elem is not None and author_elem.text else ""

        for item in channel.findall("item"):
            entry = self._parse_rss_item(item)
            feed.entries.append(entry)

        return feed

    def _parse_rss_item(self, item: ET_Element) -> FeedEntry:
        """Parse a single RSS item."""
        entry = FeedEntry()

        title_elem = item.find("title")
        entry.title = title_elem.text if title_elem is not None and title_elem.text else ""

        link_elem = item.find("link")
        entry.link = link_elem.text if link_elem is not None and link_elem.text else ""

        desc_elem = item.find("description")
        entry.summary = desc_elem.text if desc_elem is not None and desc_elem.text else ""

        content_elem = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        if content_elem is None:
            content_elem = item.find("content:encoded")
        entry.content = content_elem.text if content_elem is not None and content_elem.text else ""

        author_elem = item.find("author")
        if author_elem is None:
            author_elem = item.find("dc:creator")
        entry.author = author_elem.text if author_elem is not None and author_elem.text else ""

        pub_elem = item.find("pubDate")
        entry.published = pub_elem.text if pub_elem is not None and pub_elem.text else None

        guid_elem = item.find("guid")
        entry.guid = guid_elem.text if guid_elem is not None and guid_elem.text else entry.link

        for cat in item.findall("category"):
            if cat.text:
                entry.categories.append(cat.text)

        return entry

    def _parse_atom(self, root: ET_Element, feed_url: str) -> Feed:
        """Parse Atom feed."""
        ns = {"atom": self.ATOM_NS}
        feed = Feed(feed_url=feed_url)

        title_elem = root.find("atom:title", ns)
        if title_elem is None:
            title_elem = root.find("title")
        feed.title = title_elem.text if title_elem is not None and title_elem.text else ""

        link_elem = root.find("atom:link[@rel='alternate']", ns)
        if link_elem is None:
            links = root.findall("atom:link", ns)
            for link in links:
                if link.get("rel") == "alternate" or link.get("rel") is None:
                    link_elem = link
                    break
        feed.link = link_elem.get("href", "") if link_elem is not None else ""

        desc_elem = root.find("atom:subtitle", ns)
        if desc_elem is None:
            desc_elem = root.find("subtitle")
        feed.description = desc_elem.text if desc_elem is not None and desc_elem.text else ""

        author_elem = root.find("atom:author", ns)
        if author_elem is not None:
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is None:
                name_elem = author_elem.find("name")
            feed.author = name_elem.text if name_elem is not None and name_elem.text else ""

        for entry_elem in root.findall("atom:entry", ns):
            if entry_elem is None:
                break
            entry = self._parse_atom_entry(entry_elem, ns)
            feed.entries.append(entry)

        return feed

    def _parse_atom_entry(self, entry_elem: ET_Element, ns: dict) -> FeedEntry:
        """Parse a single Atom entry."""
        entry = FeedEntry()

        entry.title = self._atom_text(entry_elem, "title", ns)

        link_elem = self._find_atom_link(entry_elem, ns)
        entry.link = link_elem.get("href", "") if link_elem is not None else ""

        entry.summary = self._atom_text(entry_elem, "summary", ns)
        entry.content = self._atom_text(entry_elem, "content", ns)

        author_elem = entry_elem.find("atom:author", ns)
        if author_elem is None:
            author_elem = entry_elem.find("author")
        if author_elem is not None:
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is None:
                name_elem = author_elem.find("name")
            entry.author = name_elem.text if name_elem is not None and name_elem.text else ""

        entry.published = self._atom_text_or_none(entry_elem, "published", ns)
        entry.updated = self._atom_text_or_none(entry_elem, "updated", ns)

        id_elem = self._atom_find_fallback(entry_elem, "id", ns)
        entry.guid = id_elem.text if id_elem is not None and id_elem.text else entry.link

        for cat in entry_elem.findall("atom:category", ns):
            term = cat.get("term")
            if term:
                entry.categories.append(term)

        return entry

    @staticmethod
    def _atom_find_fallback(
        parent: ET_Element, tag: str, ns: dict
    ) -> ET_Element | None:
        """Find an element with namespace fallback."""
        elem = parent.find(f"atom:{tag}", ns)
        if elem is None:
            elem = parent.find(tag)
        return elem

    @staticmethod
    def _atom_text(
        parent: ET_Element, tag: str, ns: dict
    ) -> str:
        """Find an element with namespace fallback and return its text, or ''."""
        elem = parent.find(f"atom:{tag}", ns)
        if elem is None:
            elem = parent.find(tag)
        return elem.text if elem is not None and elem.text else ""

    @staticmethod
    def _atom_text_or_none(
        parent: ET_Element, tag: str, ns: dict
    ) -> str | None:
        """Find an element with namespace fallback and return its text, or None."""
        elem = parent.find(f"atom:{tag}", ns)
        if elem is None:
            elem = parent.find(tag)
        return elem.text if elem is not None and elem.text else None

    @staticmethod
    def _find_atom_link(
        parent: ET_Element, ns: dict
    ) -> ET_Element | None:
        """Find the alternate link element in an Atom entry or feed."""
        link = parent.find("atom:link[@rel='alternate']", ns)
        if link is None:
            for link in parent.findall("atom:link", ns):
                if link.get("rel") == "alternate" or link.get("rel") is None:
                    return link
        return link

    @staticmethod
    def is_feed(xml_content: str) -> bool:
        """Check if XML content appears to be a feed."""
        if not xml_content:
            return False
        patterns = [
            r"<\s*rss\b",
            r"<\s*feed\b",
            r"<\s*channel\b",
            r"xmlns.*atom",
            r"xmlns.*rss",
        ]
        return any(re.search(pattern, xml_content[:500], re.IGNORECASE) for pattern in patterns)
