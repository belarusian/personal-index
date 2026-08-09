"""Content thumbnail module - generate thumbnails for saved items."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class ThumbnailSize:
    """Thumbnail size configuration."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"

    _PRESETS = {
        "small": (64, 64),
        "medium": (128, 128),
        "large": (256, 256),
        "xlarge": (512, 512),
    }

    def __init__(self, width: int = 128, height: int = 128) -> None:
        self.width = width
        self.height = height

    def area(self) -> int:
        """Calculate the area of the thumbnail."""
        return self.width * self.height

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ThumbnailSize):
            return self.width == other.width and self.height == other.height
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.width, self.height))


class ThumbnailFormat(str, Enum):
    """Image format for thumbnails."""

    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    SVG = "svg"

    def mime_type(self) -> str:
        """Get the MIME type for this format."""
        mime_map = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }
        return mime_map[self.value]

    def extension(self) -> str:
        """Get the file extension for this format."""
        return f".{self.value}"


class ThumbnailStyle(str, Enum):
    """Visual style for thumbnails."""

    SIMPLE = "simple"
    GRADIENT = "gradient"
    CARD = "card"
    MINIMAL = "minimal"


class ThumbnailStatus(str, Enum):
    """Status of thumbnail generation."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class ThumbnailConfig:
    """Configuration for thumbnail generation."""

    size: ThumbnailSize = field(default_factory=lambda: ThumbnailSize(128, 128))
    format: ThumbnailFormat = ThumbnailFormat.PNG
    style: ThumbnailStyle = ThumbnailStyle.SIMPLE
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    border_radius: int = 0
    include_domain: bool = True
    include_title: bool = True
    max_title_length: int = 50
    cache_ttl_seconds: int = 86400

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "size": {"width": self.size.width, "height": self.size.height},
            "format": self.format.value,
            "style": self.style.value,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "border_radius": self.border_radius,
            "include_domain": self.include_domain,
            "include_title": self.include_title,
            "max_title_length": self.max_title_length,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThumbnailConfig":
        """Deserialize from dictionary."""
        size_data = data.get("size", {})
        size = ThumbnailSize(
            width=size_data.get("width", 128),
            height=size_data.get("height", 128),
        )
        fmt = data.get("format", "png")
        if isinstance(fmt, str):
            fmt = ThumbnailFormat(fmt)
        style = data.get("style", "simple")
        if isinstance(style, str):
            style = ThumbnailStyle(style)
        return cls(
            size=size,
            format=fmt,
            style=style,
            background_color=data.get("background_color", "#ffffff"),
            text_color=data.get("text_color", "#333333"),
            border_radius=data.get("border_radius", 0),
            include_domain=data.get("include_domain", True),
            include_title=data.get("include_title", True),
            max_title_length=data.get("max_title_length", 50),
            cache_ttl_seconds=data.get("cache_ttl_seconds", 86400),
        )


@dataclass
class ThumbnailMetadata:
    """Metadata about a generated thumbnail."""

    url: str
    thumbnail_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    domain: str = ""
    favicon_url: Optional[str] = None
    og_image_url: Optional[str] = None
    color_scheme: str = "light"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    config_hash: str = ""

    def is_expired(self) -> bool:
        """Check if the thumbnail metadata has expired."""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > expires
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "thumbnail_id": self.thumbnail_id,
            "title": self.title,
            "domain": self.domain,
            "favicon_url": self.favicon_url,
            "og_image_url": self.og_image_url,
            "color_scheme": self.color_scheme,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "config_hash": self.config_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThumbnailMetadata":
        """Deserialize from dictionary."""
        return cls(
            url=data["url"],
            thumbnail_id=data.get("thumbnail_id", uuid.uuid4().hex[:12]),
            title=data.get("title", ""),
            domain=data.get("domain", ""),
            favicon_url=data.get("favicon_url"),
            og_image_url=data.get("og_image_url"),
            color_scheme=data.get("color_scheme", "light"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc).isoformat()),
            expires_at=data.get("expires_at"),
            config_hash=data.get("config_hash", ""),
        )


@dataclass
class ThumbnailResult:
    """Result of thumbnail generation."""

    thumbnail_id: str
    url: str
    status: ThumbnailStatus = ThumbnailStatus.PENDING
    data: Optional[str] = None  # Base64 encoded image data
    svg_content: Optional[str] = None  # SVG content for SVG format
    width: int = 0
    height: int = 0
    format: ThumbnailFormat = ThumbnailFormat.PNG
    error: Optional[str] = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cache_key: str = ""

    def is_ready(self) -> bool:
        """Check if the thumbnail is ready."""
        return self.status in (ThumbnailStatus.READY, ThumbnailStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if the thumbnail generation failed."""
        return self.status == ThumbnailStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "thumbnail_id": self.thumbnail_id,
            "url": self.url,
            "status": self.status.value,
            "data": self.data,
            "svg_content": self.svg_content,
            "width": self.width,
            "height": self.height,
            "format": self.format.value,
            "error": self.error,
            "generated_at": self.generated_at,
            "cache_key": self.cache_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThumbnailResult":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = ThumbnailStatus(status)
        fmt = data.get("format", "png")
        if isinstance(fmt, str):
            fmt = ThumbnailFormat(fmt)
        return cls(
            thumbnail_id=data["thumbnail_id"],
            url=data["url"],
            status=status,
            data=data.get("data"),
            svg_content=data.get("svg_content"),
            width=data.get("width", 0),
            height=data.get("height", 0),
            format=fmt,
            error=data.get("error"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc).isoformat()),
            cache_key=data.get("cache_key", ""),
        )


class ThumbnailGenerator:
    """Generates thumbnail images for saved content."""

    def __init__(self, config: Optional[ThumbnailConfig] = None) -> None:
        self.config = config or ThumbnailConfig()
        self._cache: dict[str, ThumbnailResult] = {}

    def _compute_cache_key(self, url: str, config: Optional[ThumbnailConfig] = None) -> str:
        """Compute a cache key for a URL and config."""
        cfg = config or self.config
        cfg_dict = cfg.to_dict()
        cfg_dict["url"] = url
        raw = str(sorted(cfg_dict.items()))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def generate_svg_thumbnail(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        config: Optional[ThumbnailConfig] = None,
    ) -> str:
        """Generate an SVG thumbnail."""
        cfg = config or self.config
        width = cfg.size.width
        height = cfg.size.height
        bg = cfg.background_color
        text_color = cfg.text_color
        radius = cfg.border_radius

        if not domain:
            try:
                domain = urlparse(url).hostname or url
            except Exception:
                domain = url

        # Truncate title
        display_title = title[: cfg.max_title_length] if title else domain
        if len(display_title) > cfg.max_title_length:
            display_title = display_title[: cfg.max_title_length - 3] + "..."

        # Build SVG
        svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']

        # Background
        if cfg.style == ThumbnailStyle.GRADIENT:
            svg_parts.append(
                f'<defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">'
                f'<stop offset="0%" stop-color="{bg}"/>'
                f'<stop offset="100%" stop-color="{text_color}"/>'
                f"</linearGradient></defs>"
            )
            fill = "url(#bg)"
        else:
            fill = bg

        if radius > 0:
            svg_parts.append(
                f'<rect width="{width}" height="{height}" rx="{radius}" ry="{radius}" fill="{fill}"/>'
            )
        else:
            svg_parts.append(
                f'<rect width="{width}" height="{height}" fill="{fill}"/>'
            )

        # Domain text
        if cfg.include_domain:
            domain_text = domain[:30]
            svg_parts.append(
                f'<text x="{width // 2}" y="{height // 2 - 10}" '
                f'text-anchor="middle" fill="{text_color}" font-size="10" '
                f'font-family="sans-serif">{domain_text}</text>'
            )

        # Title text
        if cfg.include_title and title:
            svg_parts.append(
                f'<text x="{width // 2}" y="{height // 2 + 10}" '
                f'text-anchor="middle" fill="{text_color}" font-size="12" '
                f'font-family="sans-serif">{display_title}</text>'
            )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def generate_thumbnail(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        config: Optional[ThumbnailConfig] = None,
    ) -> ThumbnailResult:
        """Generate a thumbnail for a URL."""
        cfg = config or self.config
        cache_key = self._compute_cache_key(url, cfg)

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.status = ThumbnailStatus.CACHED
            return cached

        thumbnail_id = uuid.uuid4().hex[:12]

        try:
            if cfg.format == ThumbnailFormat.SVG:
                svg_content = self.generate_svg_thumbnail(
                    url, title, domain, favicon_url, cfg
                )
                result = ThumbnailResult(
                    thumbnail_id=thumbnail_id,
                    url=url,
                    status=ThumbnailStatus.READY,
                    svg_content=svg_content,
                    width=cfg.size.width,
                    height=cfg.size.height,
                    format=cfg.format,
                    cache_key=cache_key,
                )
            else:
                # For non-SVG formats, generate SVG as placeholder
                svg_content = self.generate_svg_thumbnail(
                    url, title, domain, favicon_url, cfg
                )
                result = ThumbnailResult(
                    thumbnail_id=thumbnail_id,
                    url=url,
                    status=ThumbnailStatus.READY,
                    svg_content=svg_content,
                    data=svg_content,  # Store SVG as data for non-SVG formats too
                    width=cfg.size.width,
                    height=cfg.size.height,
                    format=cfg.format,
                    cache_key=cache_key,
                )

            self._cache[cache_key] = result
            return result

        except Exception as e:
            result = ThumbnailResult(
                thumbnail_id=thumbnail_id,
                url=url,
                status=ThumbnailStatus.FAILED,
                error=str(e),
                format=cfg.format,
                cache_key=cache_key,
            )
            return result

    def get_cached(self, url: str, config: Optional[ThumbnailConfig] = None) -> Optional[ThumbnailResult]:
        """Get a cached thumbnail result."""
        cache_key = self._compute_cache_key(url, config)
        return self._cache.get(cache_key)

    def clear_cache(self) -> int:
        """Clear the thumbnail cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count


class ThumbnailProcessor:
    """Processes and manages thumbnail generation for multiple items."""

    def __init__(self, config: Optional[ThumbnailConfig] = None) -> None:
        self.config = config or ThumbnailConfig()
        self.generator = ThumbnailGenerator(self.config)
        self._results: dict[str, ThumbnailResult] = {}
        self._metadata: dict[str, ThumbnailMetadata] = {}

    def process_url(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        og_image_url: Optional[str] = None,
        config: Optional[ThumbnailConfig] = None,
    ) -> ThumbnailResult:
        """Process a single URL and generate its thumbnail."""
        result = self.generator.generate_thumbnail(url, title, domain, favicon_url, config)
        self._results[result.thumbnail_id] = result

        # Store metadata
        cfg = config or self.config
        cfg_hash = hashlib.sha256(str(cfg.to_dict()).encode()).hexdigest()[:8]
        expires = None
        if cfg.cache_ttl_seconds > 0:
            exp_time = datetime.now(timezone.utc) + timedelta(seconds=cfg.cache_ttl_seconds)
            expires = exp_time.isoformat()

        meta = ThumbnailMetadata(
            url=url,
            thumbnail_id=result.thumbnail_id,
            title=title,
            domain=domain,
            favicon_url=favicon_url,
            og_image_url=og_image_url,
            config_hash=cfg_hash,
            expires_at=expires,
        )
        self._metadata[url] = meta

        return result

    def process_batch(
        self,
        items: list[dict],
    ) -> list[ThumbnailResult]:
        """Process a batch of items. Each item is a dict with url, title, domain keys."""
        results = []
        for item in items:
            result = self.process_url(
                url=item.get("url", ""),
                title=item.get("title", ""),
                domain=item.get("domain", ""),
                favicon_url=item.get("favicon_url"),
                og_image_url=item.get("og_image_url"),
            )
            results.append(result)
        return results

    def get_result(self, thumbnail_id: str) -> Optional[ThumbnailResult]:
        """Get a result by thumbnail ID."""
        return self._results.get(thumbnail_id)

    def get_metadata(self, url: str) -> Optional[ThumbnailMetadata]:
        """Get metadata for a URL."""
        return self._metadata.get(url)

    def get_all_results(self) -> list[ThumbnailResult]:
        """Get all results."""
        return list(self._results.values())

    def get_all_metadata(self) -> list[ThumbnailMetadata]:
        """Get all metadata."""
        return list(self._metadata.values())

    def get_ready_count(self) -> int:
        """Count ready thumbnails."""
        return sum(1 for r in self._results.values() if r.is_ready())

    def get_failed_count(self) -> int:
        """Count failed thumbnails."""
        return sum(1 for r in self._results.values() if r.is_failed())

    def get_summary(self) -> dict:
        """Get a summary of processing."""
        return {
            "total": len(self._results),
            "ready": self.get_ready_count(),
            "failed": self.get_failed_count(),
            "pending": sum(1 for r in self._results.values() if r.status == ThumbnailStatus.PENDING),
        }

    def to_dict(self) -> dict:
        """Serialize all results and metadata."""
        return {
            "results": {tid: r.to_dict() for tid, r in self._results.items()},
            "metadata": {url: m.to_dict() for url, m in self._metadata.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThumbnailProcessor":
        """Deserialize from dictionary."""
        processor = cls()
        for tid, rdata in data.get("results", {}).items():
            processor._results[tid] = ThumbnailResult.from_dict(rdata)
        for url, mdata in data.get("metadata", {}).items():
            processor._metadata[url] = ThumbnailMetadata.from_dict(mdata)
        return processor


class ThumbnailEngine:
    """High-level engine for thumbnail operations."""

    def __init__(self, config: Optional[ThumbnailConfig] = None) -> None:
        self.config = config or ThumbnailConfig()
        self.processor = ThumbnailProcessor(self.config)
        self.generator = ThumbnailGenerator(self.config)

    def generate(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        og_image_url: Optional[str] = None,
    ) -> ThumbnailResult:
        """Generate a thumbnail for a URL."""
        return self.processor.process_url(
            url, title, domain, favicon_url, og_image_url
        )

    def generate_batch(
        self,
        items: list[dict],
    ) -> list[ThumbnailResult]:
        """Generate thumbnails for multiple items."""
        return self.processor.process_batch(items)

    def get_svg(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
    ) -> str:
        """Get SVG thumbnail content directly."""
        return self.generator.generate_svg_thumbnail(url, title, domain, favicon_url)

    def get_summary(self) -> dict:
        """Get processing summary."""
        return self.processor.get_summary()

    def get_metadata(self, url: str) -> Optional[ThumbnailMetadata]:
        """Get metadata for a URL."""
        return self.processor.get_metadata(url)
