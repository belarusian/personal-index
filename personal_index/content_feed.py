"""RSS/Atom feed generation for personal-index recent saves."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class FeedFormat(str, Enum):
    """Supported feed formats."""

    RSS = "rss"
    ATOM = "atom"


@dataclass
class FeedItem:
    """A single item in a feed."""

    title: str
    link: str
    id: str = ""
    description: str = ""
    author: str = ""
    categories: list[str] = field(default_factory=list)
    published: Optional[datetime] = None
    updated: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set defaults for id, published, and updated after init."""
        if not self.id:
            self.id = self.link
        if not self.published:
            self.published = datetime.now(timezone.utc)
        if not self.updated:
            self.updated = self.published

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "title": self.title,
            "link": self.link,
            "id": self.id,
            "description": self.description,
            "author": self.author,
            "categories": list(self.categories),
            "published": self.published.isoformat() if self.published else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedItem":
        """Deserialize from dictionary."""
        published = data.get("published")
        if isinstance(published, str) and published:
            try:
                published = datetime.fromisoformat(published)
            except ValueError:
                published = None

        updated = data.get("updated")
        if isinstance(updated, str) and updated:
            try:
                updated = datetime.fromisoformat(updated)
            except ValueError:
                updated = None

        return cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            id=data.get("id", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            categories=data.get("categories", []),
            published=published,
            updated=updated,
        )


@dataclass
class FeedGenerator:
    """Generates RSS and Atom feeds."""

    title: str
    link: str
    description: str = ""
    items: list[FeedItem] = field(default_factory=list)
    language: str = "en-us"
    ttl: int = 60
    generator: str = "personal-index"
    max_items: int = 100
    feed_id: str = ""

    def __post_init__(self) -> None:
        """Set default feed_id after init."""
        if not self.feed_id:
            self.feed_id = self.link

    def add_item(self, item: FeedItem) -> None:
        """Add an item to the feed."""
        self.items.append(item)
        # Sort by published date, newest first
        self.items.sort(key=lambda i: i.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        # Enforce max items
        if len(self.items) > self.max_items:
            self.items = self.items[: self.max_items]

    def add_items(self, items: list[FeedItem]) -> None:
        """Add multiple items to the feed."""
        for item in items:
            self.add_item(item)

    def clear(self) -> None:
        """Remove all items from the feed."""
        self.items.clear()

    def get_feed_type(self, fmt: FeedFormat) -> str:
        """Get the MIME type for a feed format."""
        if fmt == FeedFormat.RSS:
            return "application/rss+xml"
        return "application/atom+xml"

    def _escape(self, text: str) -> str:
        """Escape HTML entities."""
        return html.escape(text, quote=True)

    def _format_rss_date(self, dt: Optional[datetime]) -> str:
        """Format datetime for RSS."""
        if dt is None:
            return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")

    def _format_atom_date(self, dt: Optional[datetime]) -> str:
        """Format datetime for Atom."""
        if dt is None:
            return datetime.now(timezone.utc).isoformat()
        return dt.isoformat()

    def generate(self, fmt: FeedFormat = FeedFormat.RSS) -> str:
        """Generate feed content in the specified format."""
        if fmt == FeedFormat.RSS:
            return self._generate_rss()
        return self._generate_atom()

    def _generate_rss(self) -> str:
        """Generate RSS 2.0 feed."""
        now = self._format_rss_date(datetime.now(timezone.utc))
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0">',
            '  <channel>',
            f'    <title>{self._escape(self.title)}</title>',
            f'    <link>{self._escape(self.link)}</link>',
            f'    <description>{self._escape(self.description)}</description>',
            f'    <language>{self._escape(self.language)}</language>',
            f'    <ttl>{self.ttl}</ttl>',
            f'    <generator>{self._escape(self.generator)}</generator>',
            f'    <lastBuildDate>{now}</lastBuildDate>',
        ]

        for item in self.items:
            lines.append('    <item>')
            lines.append(f'      <title>{self._escape(item.title)}</title>')
            lines.append(f'      <link>{self._escape(item.link)}</link>')
            lines.append(f'      <guid>{self._escape(item.id)}</guid>')
            if item.description:
                lines.append(f'      <description>{self._escape(item.description)}</description>')
            if item.author:
                lines.append(f'      <author>{self._escape(item.author)}</author>')
            for cat in item.categories:
                lines.append(f'      <category>{self._escape(cat)}</category>')
            if item.published:
                lines.append(f'      <pubDate>{self._format_rss_date(item.published)}</pubDate>')
            lines.append('    </item>')

        lines.append('  </channel>')
        lines.append('</rss>')
        return "\n".join(lines)

    def _generate_atom(self) -> str:
        """Generate Atom 1.0 feed."""
        now = self._format_atom_date(datetime.now(timezone.utc))
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<feed xmlns="http://www.w3.org/2005/Atom">',
            f'  <title>{self._escape(self.title)}</title>',
            f'  <link href="{self._escape(self.link)}" rel="self"/>',
            f'  <id>{self._escape(self.feed_id)}</id>',
            f'  <updated>{now}</updated>',
            f'  <generator>{self._escape(self.generator)}</generator>',
        ]
        if self.description:
            lines.append(f'  <subtitle>{self._escape(self.description)}</subtitle>')

        for item in self.items:
            lines.append('  <entry>')
            lines.append(f'    <title>{self._escape(item.title)}</title>')
            lines.append(f'    <link href="{self._escape(item.link)}"/>')
            lines.append(f'    <id>{self._escape(item.id)}</id>')
            lines.append(f'    <updated>{self._format_atom_date(item.updated)}</updated>')
            if item.published:
                lines.append(f'    <published>{self._format_atom_date(item.published)}</published>')
            if item.description:
                lines.append(f'    <summary>{self._escape(item.description)}</summary>')
            if item.author:
                lines.append('    <author>')
                lines.append(f'      <name>{self._escape(item.author)}</name>')
                lines.append('    </author>')
            for cat in item.categories:
                lines.append(f'    <category term="{self._escape(cat)}"/>')
            lines.append('  </entry>')

        lines.append('</feed>')
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "language": self.language,
            "ttl": self.ttl,
            "generator": self.generator,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedGenerator":
        """Deserialize from dictionary."""
        items = [FeedItem.from_dict(d) for d in data.get("items", [])]
        gen = cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            description=data.get("description", ""),
            language=data.get("language", "en-us"),
            ttl=data.get("ttl", 60),
            generator=data.get("generator", "personal-index"),
        )
        gen.items = items
        return gen
