"""Content Open Graph module - extract Open Graph metadata from HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse


class OpenGraphType(str, Enum):
    """Open Graph content type."""

    ARTICLE = "article"
    WEBSITE = "website"
    VIDEO = "video"
    MUSIC = "music"
    PROFILE = "profile"
    BOOK = "book"

    @classmethod
    def from_string(cls, value: str) -> "OpenGraphType":
        """Create from string, defaulting to WEBSITE."""
        try:
            return cls(value)
        except ValueError:
            return cls.WEBSITE


class OpenGraphStatus(str, Enum):
    """Status of Open Graph extraction."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class OpenGraphImage:
    """An Open Graph image."""

    url: str
    width: int = 0
    height: int = 0
    type: str = ""
    alt: str = ""

    def __post_init__(self) -> None:
        if not self.type and self.url:
            url_lower = self.url.lower()
            if url_lower.endswith(".png"):
                self.type = "png"
            elif url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
                self.type = "jpg"
            elif url_lower.endswith(".gif"):
                self.type = "gif"
            elif url_lower.endswith(".svg"):
                self.type = "svg"
            elif url_lower.endswith(".webp"):
                self.type = "webp"

    def is_valid(self) -> bool:
        """Check if the image has a valid URL."""
        return bool(self.url)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "type": self.type,
            "alt": self.alt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpenGraphImage":
        """Deserialize from dictionary."""
        return cls(
            url=data.get("url", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            type=data.get("type", ""),
            alt=data.get("alt", ""),
        )


@dataclass
class OpenGraphConfig:
    """Configuration for Open Graph extraction."""

    cache_ttl_seconds: int = 86400
    timeout_seconds: int = 10
    max_images: int = 5
    include_twitter_cards: bool = True
    include_microdata: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_images": self.max_images,
            "include_twitter_cards": self.include_twitter_cards,
            "include_microdata": self.include_microdata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpenGraphConfig":
        """Deserialize from dictionary."""
        return cls(
            cache_ttl_seconds=data.get("cache_ttl_seconds", 86400),
            timeout_seconds=data.get("timeout_seconds", 10),
            max_images=data.get("max_images", 5),
            include_twitter_cards=data.get("include_twitter_cards", True),
            include_microdata=data.get("include_microdata", False),
        )


@dataclass
class OpenGraphMetadata:
    """Extracted Open Graph metadata."""

    url: str
    title: str = ""
    description: str = ""
    type: OpenGraphType = OpenGraphType.WEBSITE
    site_name: str = ""
    locale: str = ""
    images: list[OpenGraphImage] = field(default_factory=list)
    twitter_card: str = ""
    twitter_images: list[OpenGraphImage] = field(default_factory=list)
    twitter_site: str = ""
    twitter_creator: str = ""
    video_url: str = ""
    audio_url: str = ""
    determiner: str = ""
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def has_complete_info(self) -> bool:
        """Check if essential metadata is present."""
        return bool(self.title) and bool(self.description) and len(self.images) > 0

    def get_primary_image(self) -> Optional[OpenGraphImage]:
        """Get the primary (first) image."""
        if self.images:
            return self.images[0]
        if self.twitter_images:
            return self.twitter_images[0]
        return None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "site_name": self.site_name,
            "locale": self.locale,
            "images": [img.to_dict() for img in self.images],
            "twitter_card": self.twitter_card,
            "twitter_images": [img.to_dict() for img in self.twitter_images],
            "twitter_site": self.twitter_site,
            "twitter_creator": self.twitter_creator,
            "video_url": self.video_url,
            "audio_url": self.audio_url,
            "determiner": self.determiner,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpenGraphMetadata":
        """Deserialize from dictionary."""
        og_type = data.get("type", "website")
        if isinstance(og_type, str):
            og_type = OpenGraphType.from_string(og_type)
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            type=og_type,
            site_name=data.get("site_name", ""),
            locale=data.get("locale", ""),
            images=[OpenGraphImage.from_dict(img) for img in data.get("images", [])],
            twitter_card=data.get("twitter_card", ""),
            twitter_images=[OpenGraphImage.from_dict(img) for img in data.get("twitter_images", [])],
            twitter_site=data.get("twitter_site", ""),
            twitter_creator=data.get("twitter_creator", ""),
            video_url=data.get("video_url", ""),
            audio_url=data.get("audio_url", ""),
            determiner=data.get("determiner", ""),
            extracted_at=data.get("extracted_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class OpenGraphResult:
    """Result of Open Graph extraction."""

    url: str
    status: OpenGraphStatus = OpenGraphStatus.PENDING
    metadata: Optional[OpenGraphMetadata] = None
    error: Optional[str] = None
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def title(self) -> str:
        """Shortcut to metadata title."""
        return self.metadata.title if self.metadata else ""

    @property
    def description(self) -> str:
        """Shortcut to metadata description."""
        return self.metadata.description if self.metadata else ""

    @property
    def images(self) -> list[OpenGraphImage]:
        """Shortcut to metadata images."""
        return self.metadata.images if self.metadata else []

    @property
    def type(self) -> OpenGraphType:
        """Shortcut to metadata type."""
        return self.metadata.type if self.metadata else OpenGraphType.WEBSITE

    @property
    def site_name(self) -> str:
        """Shortcut to metadata site_name."""
        return self.metadata.site_name if self.metadata else ""

    def is_ready(self) -> bool:
        """Check if the result is ready."""
        return self.status in (OpenGraphStatus.READY, OpenGraphStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if the extraction failed."""
        return self.status == OpenGraphStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "status": self.status.value,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "error": self.error,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpenGraphResult":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = OpenGraphStatus(status)
        meta_data = data.get("metadata")
        metadata = None
        if meta_data:
            metadata = OpenGraphMetadata.from_dict(meta_data)
        return cls(
            url=data.get("url", ""),
            status=status,
            metadata=metadata,
            error=data.get("error"),
            extracted_at=data.get("extracted_at", datetime.now(timezone.utc).isoformat()),
        )


class OpenGraphParser(HTMLParser):
    """Parse HTML to extract Open Graph and Twitter Card metadata."""

    def __init__(self) -> None:
        super().__init__()
        self.og_tags: dict[str, list[str]] = {}
        self.twitter_tags: dict[str, list[str]] = {}
        self._current_property: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "meta":
            attr_dict = dict(attrs)
            property_name = attr_dict.get("property")
            content = attr_dict.get("content", "")

            if property_name and property_name.startswith("og:"):
                prop = property_name[3:]  # Remove "og:" prefix
                if prop not in self.og_tags:
                    self.og_tags[prop] = []
                self.og_tags[prop].append(content)
                return

            name = attr_dict.get("name")
            if name and name.startswith("twitter:"):
                prop = name[8:]  # Remove "twitter:" prefix
                if prop not in self.twitter_tags:
                    self.twitter_tags[prop] = []
                self.twitter_tags[prop].append(content)

    def parse(self, html: str, base_url: str) -> OpenGraphMetadata:
        """Parse HTML and return OpenGraphMetadata."""
        try:
            self.feed(html)
        except Exception:
            pass

        # Extract images with dimensions
        images = []
        image_urls = self.og_tags.get("image", [])
        image_widths = self.og_tags.get("image:width", ["0"])
        image_heights = self.og_tags.get("image:height", ["0"])
        image_als = self.og_tags.get("image:alt", [""])

        for i, url in enumerate(image_urls):
            width = int(image_widths[i]) if i < len(image_widths) else 0
            height = int(image_heights[i]) if i < len(image_heights) else 0
            alt = image_als[i] if i < len(image_als) else ""
            images.append(OpenGraphImage(url=url, width=width, height=height, alt=alt))

        # Extract twitter images
        twitter_images = []
        twitter_image_urls = self.twitter_tags.get("image", [])
        for url in twitter_image_urls:
            twitter_images.append(OpenGraphImage(url=url))

        og_type = self.og_tags.get("type", ["website"])[0] if self.og_tags.get("type") else "website"

        return OpenGraphMetadata(
            url=self.og_tags.get("url", [base_url])[0] if self.og_tags.get("url") else base_url,
            title=self.og_tags.get("title", [""])[0] if self.og_tags.get("title") else "",
            description=self.og_tags.get("description", [""])[0] if self.og_tags.get("description") else "",
            type=OpenGraphType.from_string(og_type),
            site_name=self.og_tags.get("site_name", [""])[0] if self.og_tags.get("site_name") else "",
            locale=self.og_tags.get("locale", [""])[0] if self.og_tags.get("locale") else "",
            images=images,
            twitter_card=self.twitter_tags.get("card", [""])[0] if self.twitter_tags.get("card") else "",
            twitter_images=twitter_images,
            twitter_site=self.twitter_tags.get("site", [""])[0] if self.twitter_tags.get("site") else "",
            twitter_creator=self.twitter_tags.get("creator", [""])[0] if self.twitter_tags.get("creator") else "",
            video_url=self.og_tags.get("video", [""])[0] if self.og_tags.get("video") else "",
            audio_url=self.og_tags.get("audio", [""])[0] if self.og_tags.get("audio") else "",
            determiner=self.og_tags.get("determiner", [""])[0] if self.og_tags.get("determiner") else "",
        )


class OpenGraphExtractor:
    """Extract Open Graph metadata from HTML content."""

    def __init__(self, config: Optional[OpenGraphConfig] = None) -> None:
        self.config = config or OpenGraphConfig()

    def extract(self, html: str, url: str) -> OpenGraphMetadata:
        """Extract Open Graph metadata from HTML."""
        if not html:
            return OpenGraphMetadata(url=url)

        parser = OpenGraphParser()
        metadata = parser.parse(html, url)

        # Apply max_images limit
        if len(metadata.images) > self.config.max_images:
            metadata.images = metadata.images[: self.config.max_images]

        # If twitter cards not included, clear them
        if not self.config.include_twitter_cards:
            metadata.twitter_card = ""
            metadata.twitter_images = []
            metadata.twitter_site = ""
            metadata.twitter_creator = ""

        return metadata


class OpenGraphStore:
    """Store and retrieve Open Graph metadata."""

    def __init__(self) -> None:
        self._store: dict[str, OpenGraphMetadata] = {}

    def store(self, url: str, metadata: OpenGraphMetadata) -> None:
        """Store metadata for a URL."""
        self._store[url] = metadata

    def get(self, url: str) -> Optional[OpenGraphMetadata]:
        """Get metadata for a URL."""
        return self._store.get(url)

    def remove(self, url: str) -> bool:
        """Remove metadata. Returns True if removed."""
        if url in self._store:
            del self._store[url]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored metadata."""
        self._store.clear()

    def count(self) -> int:
        """Get the number of stored entries."""
        return len(self._store)

    def all_urls(self) -> list[str]:
        """Get all URLs with stored metadata."""
        return list(self._store.keys())

    def to_dict(self) -> dict:
        """Serialize all stored metadata."""
        return {url: meta.to_dict() for url, meta in self._store.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "OpenGraphStore":
        """Deserialize from dictionary."""
        store = cls()
        for url, mdata in data.items():
            store._store[url] = OpenGraphMetadata.from_dict(mdata)
        return store


class OpenGraphManager:
    """Manage Open Graph extraction and caching."""

    def __init__(self, config: Optional[OpenGraphConfig] = None) -> None:
        self.config = config or OpenGraphConfig()
        self.extractor = OpenGraphExtractor(self.config)
        self.store = OpenGraphStore()

    def extract(self, html: str, url: str) -> OpenGraphMetadata:
        """Extract and store Open Graph metadata."""
        # Check cache
        cached = self.store.get(url)
        if cached:
            return cached

        metadata = self.extractor.extract(html, url)
        self.store.store(url, metadata)
        return metadata

    def batch_extract(self, items: list[dict]) -> list[OpenGraphMetadata]:
        """Extract metadata for multiple items. Each item has 'url' and 'html' keys."""
        results = []
        for item in items:
            metadata = self.extract(
                html=item.get("html", ""),
                url=item.get("url", ""),
            )
            results.append(metadata)
        return results

    def get_cached(self, url: str) -> Optional[OpenGraphMetadata]:
        """Get cached metadata."""
        return self.store.get(url)

    def get_summary(self) -> dict:
        """Get a summary of stored metadata."""
        with_images = sum(1 for m in self.store._store.values() if m.images)
        with_title = sum(1 for m in self.store._store.values() if m.title)
        return {
            "total": self.store.count(),
            "with_images": with_images,
            "with_title": with_title,
            "complete": sum(1 for m in self.store._store.values() if m.has_complete_info()),
        }

    def clear_cache(self) -> int:
        """Clear the cache. Returns number of entries cleared."""
        count = self.store.count()
        self.store.clear()
        return count
