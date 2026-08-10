"""RSS feed reader for personal index."""

from __future__ import annotations

import re
from defusedxml.ElementTree import fromstring as ET_fromstring, ParseError as ET_ParseError
from dataclasses import dataclass, field


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

    def _parse_rss(self, root: ET.Element, feed_url: str) -> Feed:
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

    def _parse_rss_item(self, item: ET.Element) -> FeedEntry:
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

    def _parse_atom(self, root: ET.Element, feed_url: str) -> Feed:
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
                if link.get("rel") == "alternate" or l.get("rel") is None:
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

    def _parse_atom_entry(self, entry_elem: ET.Element, ns: dict) -> FeedEntry:
        """Parse a single Atom entry."""
        entry = FeedEntry()

        title_elem = entry_elem.find("atom:title", ns)
        if title_elem is None:
            title_elem = entry_elem.find("title")
        entry.title = title_elem.text if title_elem is not None and title_elem.text else ""

        link_elem = entry_elem.find("atom:link[@rel='alternate']", ns)
        if link_elem is None:
            links = entry_elem.findall("atom:link", ns)
            for link in links:
                if link.get("rel") == "alternate" or l.get("rel") is None:
                    link_elem = link
                    break
        entry.link = link_elem.get("href", "") if link_elem is not None else ""

        summary_elem = entry_elem.find("atom:summary", ns)
        if summary_elem is None:
            summary_elem = entry_elem.find("summary")
        entry.summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

        content_elem = entry_elem.find("atom:content", ns)
        if content_elem is None:
            content_elem = entry_elem.find("content")
        entry.content = content_elem.text if content_elem is not None and content_elem.text else ""

        author_elem = entry_elem.find("atom:author", ns)
        if author_elem is not None:
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is None:
                name_elem = author_elem.find("name")
            entry.author = name_elem.text if name_elem is not None and name_elem.text else ""

        published_elem = entry_elem.find("atom:published", ns)
        if published_elem is None:
            published_elem = entry_elem.find("published")
        entry.published = published_elem.text if published_elem is not None and published_elem.text else None

        updated_elem = entry_elem.find("atom:updated", ns)
        if updated_elem is None:
            updated_elem = entry_elem.find("updated")
        entry.updated = updated_elem.text if updated_elem is not None and updated_elem.text else None

        id_elem = entry_elem.find("atom:id", ns)
        if id_elem is None:
            id_elem = entry_elem.find("id")
        entry.guid = id_elem.text if id_elem is not None and id_elem.text else entry.link

        for cat in entry_elem.findall("atom:category", ns):
            term = cat.get("term")
            if term:
                entry.categories.append(term)

        return entry

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
        for pattern in patterns:
            if re.search(pattern, xml_content[:500], re.IGNORECASE):
                return True
        return False
