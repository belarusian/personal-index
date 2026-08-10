"""Content favicon module - extract favicons from saved URLs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse


class FaviconFormat(str, Enum):
    """Format of the favicon."""

    ICO = "ico"
    PNG = "png"
    SVG = "svg"
    ANY = "any"

    def extension(self) -> str:
        """Get the file extension."""
        return f".{self.value}"

    def mime_type(self) -> str:
        """Get the MIME type."""
        mime_map = {
            "ico": "image/x-icon",
            "png": "image/png",
            "svg": "image/svg+xml",
            "any": "image/*",
        }
        return mime_map[self.value]


class FaviconSource(str, Enum):
    """Source of the favicon."""

    HEAD_TAG = "head_tag"
    DEFAULT_PATH = "default_path"
    GOOGLE_SERVICE = "google_service"
    DNS_TXT = "dns_txt"


class FaviconStatus(str, Enum):
    """Status of favicon extraction."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class FaviconConfig:
    """Configuration for favicon extraction."""

    preferred_format: FaviconFormat = FaviconFormat.ANY
    size: int = 32
    cache_ttl_seconds: int = 86400
    timeout_seconds: int = 10
    fallback_to_google: bool = True
    max_size_bytes: int = 102400

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "preferred_format": self.preferred_format.value,
            "size": self.size,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "timeout_seconds": self.timeout_seconds,
            "fallback_to_google": self.fallback_to_google,
            "max_size_bytes": self.max_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FaviconConfig":
        """Deserialize from dictionary."""
        fmt = data.get("preferred_format", "any")
        if isinstance(fmt, str):
            fmt = FaviconFormat(fmt)
        return cls(
            preferred_format=fmt,
            size=data.get("size", 32),
            cache_ttl_seconds=data.get("cache_ttl_seconds", 86400),
            timeout_seconds=data.get("timeout_seconds", 10),
            fallback_to_google=data.get("fallback_to_google", True),
            max_size_bytes=data.get("max_size_bytes", 102400),
        )


@dataclass
class FaviconInfo:
    """Information about a favicon."""

    url: str
    format: FaviconFormat = FaviconFormat.ICO
    size: int = 32
    source: FaviconSource = FaviconSource.DEFAULT_PATH
    width: int = 0
    height: int = 0
    type_hint: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "format": self.format.value,
            "size": self.size,
            "source": self.source.value,
            "width": self.width,
            "height": self.height,
            "type_hint": self.type_hint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FaviconInfo":
        """Deserialize from dictionary."""
        fmt = data.get("format", "ico")
        if isinstance(fmt, str):
            fmt = FaviconFormat(fmt)
        source = data.get("source", "default_path")
        if isinstance(source, str):
            source = FaviconSource(source)
        return cls(
            url=data["url"],
            format=fmt,
            size=data.get("size", 32),
            source=source,
            width=data.get("width", 0),
            height=data.get("height", 0),
            type_hint=data.get("type_hint", ""),
        )


@dataclass
class FaviconResult:
    """Result of favicon extraction."""

    domain: str
    url: str = ""
    status: FaviconStatus = FaviconStatus.PENDING
    format: FaviconFormat = FaviconFormat.ICO
    size: int = 32
    source: FaviconSource = FaviconSource.DEFAULT_PATH
    error: Optional[str] = None
    extracted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cache_key: str = ""

    def is_ready(self) -> bool:
        """Check if the favicon is ready."""
        return self.status in (FaviconStatus.READY, FaviconStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if the extraction failed."""
        return self.status == FaviconStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "domain": self.domain,
            "url": self.url,
            "status": self.status.value,
            "format": self.format.value,
            "size": self.size,
            "source": self.source.value,
            "error": self.error,
            "extracted_at": self.extracted_at,
            "cache_key": self.cache_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FaviconResult":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = FaviconStatus(status)
        fmt = data.get("format", "ico")
        if isinstance(fmt, str):
            fmt = FaviconFormat(fmt)
        source = data.get("source", "default_path")
        if isinstance(source, str):
            source = FaviconSource(source)
        return cls(
            domain=data["domain"],
            url=data.get("url", ""),
            status=status,
            format=fmt,
            size=data.get("size", 32),
            source=source,
            error=data.get("error"),
            extracted_at=data.get("extracted_at", datetime.now(timezone.utc).isoformat()),
            cache_key=data.get("cache_key", ""),
        )


class FaviconHTMLParser(HTMLParser):
    """Parse HTML to extract favicon links."""

    def __init__(self) -> None:
        """Initialize the favicon HTML parser."""
        super().__init__()
        self.favicon_links: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        """Handle start tags to find favicon links."""
        if tag.lower() == "link":
            attr_dict = dict(attrs)
            rel = attr_dict.get("rel", "")
            if rel and ("icon" in rel.lower() or "shortcut" in rel.lower() or "apple-touch" in rel.lower()):
                href = attr_dict.get("href", "")
                icon_type = attr_dict.get("type", "")
                sizes = attr_dict.get("sizes", "")
                self.favicon_links.append({
                    "href": href,
                    "type": icon_type,
                    "sizes": sizes,
                    "rel": rel,
                })


class FaviconExtractor:
    """Extract favicons from URLs and HTML content."""

    def __init__(self, config: Optional[FaviconConfig] = None) -> None:
        """Initialize the favicon extractor.

        Args:
            config: Optional favicon configuration.
        """
        self.config = config or FaviconConfig()

    def extract_domain(self, url: str) -> str:
        """Extract domain from a URL."""
        try:
            parsed = urlparse(url)
            return parsed.hostname or url
        except Exception:
            return url

    def get_favicon_url(self, url: str) -> str:
        """Get the default favicon URL for a given URL."""
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme or "https"
            hostname = parsed.hostname or url
            return f"{scheme}://{hostname}/favicon.ico"
        except Exception:
            return f"https://{url}/favicon.ico"

    def get_google_favicon_url(self, domain: str, size: int = 32) -> str:
        """Get favicon URL via Google's favicon service."""
        return f"https://www.google.com/s2/favicons?domain={domain}&s={size}"

    def _detect_format(self, url: str, type_hint: str = "") -> FaviconFormat:
        """Detect favicon format from URL or type hint."""
        if type_hint:
            if "svg" in type_hint.lower():
                return FaviconFormat.SVG
            if "png" in type_hint.lower():
                return FaviconFormat.PNG
            if "icon" in type_hint.lower() or "ico" in type_hint.lower():
                return FaviconFormat.ICO

        url_lower = url.lower()
        if url_lower.endswith(".svg"):
            return FaviconFormat.SVG
        if url_lower.endswith(".png"):
            return FaviconFormat.PNG
        if url_lower.endswith(".ico"):
            return FaviconFormat.ICO

        return FaviconFormat.ICO

    def extract_from_html(self, html: str, base_url: str) -> Optional[FaviconInfo]:
        """Extract favicon information from HTML content."""
        parser = FaviconHTMLParser()
        try:
            parser.feed(html)
        except Exception:
            pass

        if parser.favicon_links:
            # Prefer regular icon over apple-touch-icon
            preferred = None
            for link in parser.favicon_links:
                rel = link.get("rel", "").lower()
                if "apple-touch" not in rel:
                    preferred = link
                    break
            if not preferred:
                preferred = parser.favicon_links[0]

            href = preferred.get("href", "")
            icon_type = preferred.get("type", "")

            # Resolve relative URLs
            if href and not href.startswith(("http://", "https://", "//")):
                href = urljoin(base_url, href)

            fmt = self._detect_format(href, icon_type)
            return FaviconInfo(
                url=href,
                format=fmt,
                source=FaviconSource.HEAD_TAG,
                type_hint=icon_type,
            )

        # Fallback to default path
        default_url = self.get_favicon_url(base_url)
        return FaviconInfo(
            url=default_url,
            format=FaviconFormat.ICO,
            source=FaviconSource.DEFAULT_PATH,
        )


class FaviconStore:
    """Store and retrieve favicon results."""

    def __init__(self) -> None:
        """Initialize the favicon store with empty storage."""
        self._store: dict[str, FaviconResult] = {}

    def store(self, domain: str, result: FaviconResult) -> None:
        """Store a favicon result for a domain."""
        self._store[domain] = result

    def get(self, domain: str) -> Optional[FaviconResult]:
        """Get a favicon result for a domain."""
        return self._store.get(domain)

    def contains(self, domain: str) -> bool:
        """Check if a domain has a stored favicon."""
        return domain in self._store

    def remove(self, domain: str) -> bool:
        """Remove a favicon result. Returns True if removed."""
        if domain in self._store:
            del self._store[domain]
            return True
        return False

    def clear(self) -> None:
        """Clear all stored favicons."""
        self._store.clear()

    def count(self) -> int:
        """Get the number of stored favicons."""
        return len(self._store)

    def all_domains(self) -> list[str]:
        """Get all domains with stored favicons."""
        return list(self._store.keys())

    def to_dict(self) -> dict:
        """Serialize all stored results."""
        return {domain: result.to_dict() for domain, result in self._store.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "FaviconStore":
        """Deserialize from dictionary."""
        store = cls()
        for domain, rdata in data.items():
            store._store[domain] = FaviconResult.from_dict(rdata)
        return store


class FaviconManager:
    """Manage favicon extraction and caching."""

    def __init__(
        self,
        config: Optional[FaviconConfig] = None,
        fallback_to_google: bool = True,
    ) -> None:
        """Initialize the favicon manager.

        Args:
            config: Optional favicon configuration.
            fallback_to_google: Whether to use Google's favicon service as fallback.
        """
        self.config = config or FaviconConfig()
        self.fallback_to_google = fallback_to_google
        self.extractor = FaviconExtractor(self.config)
        self.store = FaviconStore()

    def extract_favicon(
        self,
        url: str,
        html: Optional[str] = None,
        fallback_google: bool = False,
    ) -> FaviconResult:
        """Extract favicon for a URL."""
        domain = self.extractor.extract_domain(url)

        # Check cache
        cached = self.store.get(domain)
        if cached and cached.is_ready():
            cached.status = FaviconStatus.CACHED
            return cached

        if html:
            info = self.extractor.extract_from_html(html, url)
        else:
            default_url = self.extractor.get_favicon_url(url)
            info = FaviconInfo(
                url=default_url,
                format=FaviconFormat.ICO,
                source=FaviconSource.DEFAULT_PATH,
            )

        if fallback_google and self.fallback_to_google:
            google_url = self.extractor.get_google_favicon_url(domain, self.config.size)
            info.url = google_url
            info.source = FaviconSource.GOOGLE_SERVICE

        result = FaviconResult(
            domain=domain,
            url=info.url,
            status=FaviconStatus.READY,
            format=info.format,
            size=info.size,
            source=info.source,
        )
        self.store.store(domain, result)
        return result

    def batch_extract(self, urls: list[str]) -> list[FaviconResult]:
        """Extract favicons for multiple URLs."""
        results = []
        for url in urls:
            result = self.extract_favicon(url)
            results.append(result)
        return results

    def get_cached(self, domain: str) -> Optional[FaviconResult]:
        """Get a cached favicon result."""
        return self.store.get(domain)

    def refresh_favicon(self, domain: str) -> FaviconResult:
        """Refresh a favicon by re-extracting."""
        self.store.remove(domain)
        return self.extract_favicon(f"https://{domain}")

    def get_summary(self) -> dict:
        """Get a summary of favicon extraction."""
        ready = sum(1 for r in self.store._store.values() if r.is_ready())
        failed = sum(1 for r in self.store._store.values() if r.is_failed())
        return {
            "total": self.store.count(),
            "ready": ready,
            "failed": failed,
        }

    def clear_cache(self) -> int:
        """Clear the favicon cache. Returns number of entries cleared."""
        count = self.store.count()
        self.store.clear()
        return count
