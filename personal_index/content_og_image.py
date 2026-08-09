"""Content OG Image module - generate Open Graph images for saved items."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class OGImageSize:
    """Size configuration for OG images."""

    FACEBOOK = "facebook"
    TWITTER_LARGE = "twitter_large"
    TWITTER_SMALL = "twitter_small"
    SQUARE = "square"
    LINKEDIN = "linkedin"

    _PRESETS = {
        "facebook": (1200, 630),
        "twitter_large": (1200, 628),
        "twitter_small": (600, 314),
        "square": (1200, 1200),
        "linkedin": (1200, 627),
    }

    def __init__(self, width: int = 1200, height: int = 630) -> None:
        self.width = width
        self.height = height

    def area(self) -> int:
        """Calculate the area."""
        return self.width * self.height

    def aspect_ratio(self) -> float:
        """Calculate the aspect ratio."""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OGImageSize):
            return self.width == other.width and self.height == other.height
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.width, self.height))


class OGImageStyle(str, Enum):
    """Visual style for OG images."""

    GRADIENT = "gradient"
    SOLID = "solid"
    PATTERN = "pattern"
    PHOTO = "photo"
    MINIMAL = "minimal"


class OGImageLayout(str, Enum):
    """Text layout for OG images."""

    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class OGImageBackground:
    """Background configuration for OG images."""

    type: str = "gradient"
    color: str = "#667eea"
    colors: list[str] = field(default_factory=lambda: ["#667eea", "#764ba2"])
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "color": self.color,
            "colors": self.colors,
            "image_url": self.image_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageBackground":
        """Deserialize from dictionary."""
        return cls(
            type=data.get("type", "gradient"),
            color=data.get("color", "#667eea"),
            colors=data.get("colors", ["#667eea", "#764ba2"]),
            image_url=data.get("image_url"),
        )


@dataclass
class OGImageTextConfig:
    """Text configuration for OG images."""

    font_family: str = "sans-serif"
    title_size: int = 48
    description_size: int = 24
    domain_size: int = 18
    title_color: str = "#000000"
    description_color: str = "#666666"
    domain_color: str = "#999999"
    title_weight: str = "bold"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "font_family": self.font_family,
            "title_size": self.title_size,
            "description_size": self.description_size,
            "domain_size": self.domain_size,
            "title_color": self.title_color,
            "description_color": self.description_color,
            "domain_color": self.domain_color,
            "title_weight": self.title_weight,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageTextConfig":
        """Deserialize from dictionary."""
        return cls(
            font_family=data.get("font_family", "sans-serif"),
            title_size=data.get("title_size", 48),
            description_size=data.get("description_size", 24),
            domain_size=data.get("domain_size", 18),
            title_color=data.get("title_color", "#000000"),
            description_color=data.get("description_color", "#666666"),
            domain_color=data.get("domain_color", "#999999"),
            title_weight=data.get("title_weight", "bold"),
        )


@dataclass
class OGImageWatermark:
    """Watermark configuration for OG images."""

    text: str = ""
    position: str = "bottom-right"
    opacity: float = 0.5
    font_size: int = 14
    color: str = "#ffffff"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "text": self.text,
            "position": self.position,
            "opacity": self.opacity,
            "font_size": self.font_size,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageWatermark":
        """Deserialize from dictionary."""
        return cls(
            text=data.get("text", ""),
            position=data.get("position", "bottom-right"),
            opacity=data.get("opacity", 0.5),
            font_size=data.get("font_size", 14),
            color=data.get("color", "#ffffff"),
        )


class OGImageStatus(str, Enum):
    """Status of OG image generation."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class OGImageConfig:
    """Configuration for OG image generation."""

    size: OGImageSize = field(default_factory=lambda: OGImageSize(1200, 630))
    style: OGImageStyle = OGImageStyle.GRADIENT
    layout: OGImageLayout = OGImageLayout.CENTER
    background: OGImageBackground = field(
        default_factory=lambda: OGImageBackground(type="gradient", colors=["#667eea", "#764ba2"])
    )
    text_config: OGImageTextConfig = field(default_factory=OGImageTextConfig)
    watermark: Optional[OGImageWatermark] = None
    cache_ttl_seconds: int = 86400
    max_title_length: int = 60
    max_description_length: int = 150
    include_domain: bool = True
    include_favicon: bool = True
    include_tags: bool = True
    border_radius: int = 0
    padding: int = 60

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "size": {"width": self.size.width, "height": self.size.height},
            "style": self.style.value,
            "layout": self.layout.value,
            "background": self.background.to_dict(),
            "text_config": self.text_config.to_dict(),
            "watermark": self.watermark.to_dict() if self.watermark else None,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "max_title_length": self.max_title_length,
            "max_description_length": self.max_description_length,
            "include_domain": self.include_domain,
            "include_favicon": self.include_favicon,
            "include_tags": self.include_tags,
            "border_radius": self.border_radius,
            "padding": self.padding,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageConfig":
        """Deserialize from dictionary."""
        size_data = data.get("size", {})
        size = OGImageSize(
            width=size_data.get("width", 1200),
            height=size_data.get("height", 630),
        )
        style = data.get("style", "gradient")
        if isinstance(style, str):
            style = OGImageStyle(style)
        layout = data.get("layout", "center")
        if isinstance(layout, str):
            layout = OGImageLayout(layout)
        bg_data = data.get("background", {})
        background = OGImageBackground.from_dict(bg_data) if bg_data else OGImageBackground()
        text_data = data.get("text_config", {})
        text_config = OGImageTextConfig.from_dict(text_data) if text_data else OGImageTextConfig()
        wm_data = data.get("watermark")
        watermark = OGImageWatermark.from_dict(wm_data) if wm_data else None
        return cls(
            size=size,
            style=style,
            layout=layout,
            background=background,
            text_config=text_config,
            watermark=watermark,
            cache_ttl_seconds=data.get("cache_ttl_seconds", 86400),
            max_title_length=data.get("max_title_length", 60),
            max_description_length=data.get("max_description_length", 150),
            include_domain=data.get("include_domain", True),
            include_favicon=data.get("include_favicon", True),
            include_tags=data.get("include_tags", True),
            border_radius=data.get("border_radius", 0),
            padding=data.get("padding", 60),
        )


@dataclass
class OGImageMetadata:
    """Metadata for OG image generation."""

    url: str
    title: str = ""
    description: str = ""
    domain: str = ""
    favicon_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    author: str = ""
    published_at: Optional[str] = None
    color_scheme: str = "light"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "domain": self.domain,
            "favicon_url": self.favicon_url,
            "tags": self.tags,
            "author": self.author,
            "published_at": self.published_at,
            "color_scheme": self.color_scheme,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageMetadata":
        """Deserialize from dictionary."""
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            domain=data.get("domain", ""),
            favicon_url=data.get("favicon_url"),
            tags=data.get("tags", []),
            author=data.get("author", ""),
            published_at=data.get("published_at"),
            color_scheme=data.get("color_scheme", "light"),
        )


@dataclass
class OGImageResult:
    """Result of OG image generation."""

    url: str
    status: OGImageStatus = OGImageStatus.PENDING
    svg_content: Optional[str] = None
    width: int = 0
    height: int = 0
    style: OGImageStyle = OGImageStyle.GRADIENT
    error: Optional[str] = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cache_key: str = ""

    def is_ready(self) -> bool:
        """Check if the image is ready."""
        return self.status in (OGImageStatus.READY, OGImageStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if generation failed."""
        return self.status == OGImageStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "status": self.status.value,
            "svg_content": self.svg_content,
            "width": self.width,
            "height": self.height,
            "style": self.style.value,
            "error": self.error,
            "generated_at": self.generated_at,
            "cache_key": self.cache_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OGImageResult":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = OGImageStatus(status)
        style = data.get("style", "gradient")
        if isinstance(style, str):
            style = OGImageStyle(style)
        return cls(
            url=data.get("url", ""),
            status=status,
            svg_content=data.get("svg_content"),
            width=data.get("width", 0),
            height=data.get("height", 0),
            style=style,
            error=data.get("error"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc).isoformat()),
            cache_key=data.get("cache_key", ""),
        )


class OGImageGenerator:
    """Generate Open Graph images as SVG."""

    def __init__(self, config: Optional[OGImageConfig] = None) -> None:
        self.config = config or OGImageConfig()
        self._cache: dict[str, OGImageResult] = {}

    def _compute_cache_key(self, url: str, config: Optional[OGImageConfig] = None) -> str:
        """Compute a cache key."""
        cfg = config or self.config
        raw = f"{url}:{cfg.style.value}:{cfg.layout.value}:{cfg.size.width}:{cfg.size.height}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def generate(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        config: Optional[OGImageConfig] = None,
    ) -> str:
        """Generate an OG image as SVG."""
        cfg = config or self.config
        cache_key = self._compute_cache_key(url, cfg)

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.status = OGImageStatus.CACHED
            return cached.svg_content or ""

        try:
            width = cfg.size.width
            height = cfg.size.height
            padding = cfg.padding
            tc = cfg.text_config

            if not domain:
                try:
                    domain = urlparse(url).hostname or url
                except Exception:
                    domain = url

            title = self._truncate_text(title, cfg.max_title_length)
            description = self._truncate_text(description, cfg.max_description_length)

            svg_parts = [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            ]

            # Defs
            svg_parts.append("<defs>")
            if cfg.style == OGImageStyle.GRADIENT:
                colors = cfg.background.colors
                svg_parts.append(
                    f'<linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
                    f'<stop offset="0%" stop-color="{colors[0]}"/>'
                    f'<stop offset="100%" stop-color="{colors[1]}"/>'
                    f"</linearGradient>"
                )
                bg_fill = "url(#bgGrad)"
            elif cfg.style == OGImageStyle.SOLID:
                bg_fill = cfg.background.color
            elif cfg.style == OGImageStyle.MINIMAL:
                bg_fill = "#ffffff"
            else:
                bg_fill = cfg.background.color
            svg_parts.append("</defs>")

            # Background
            rx = cfg.border_radius
            svg_parts.append(
                f'<rect width="{width}" height="{height}" rx="{rx}" ry="{rx}" fill="{bg_fill}"/>'
            )

            # Determine text alignment and position
            layout = cfg.layout
            if layout == OGImageLayout.LEFT:
                text_x = padding
                text_anchor = "start"
            elif layout == OGImageLayout.RIGHT:
                text_x = width - padding
                text_anchor = "end"
            else:
                text_x = width // 2
                text_anchor = "middle"

            # Calculate Y positions
            y_offset = padding + 40

            # Favicon
            if cfg.include_favicon and favicon_url:
                icon_x = text_x - (width // 4) if layout == OGImageLayout.CENTER else text_x
                svg_parts.append(
                    f'<circle cx="{icon_x}" cy="{y_offset}" r="24" fill="rgba(255,255,255,0.2)"/>'
                )
                svg_parts.append(
                    f'<text x="{icon_x}" y="{y_offset + 6}" text-anchor="middle" '
                    f'fill="rgba(255,255,255,0.6)" font-size="16" font-family="{tc.font_family}">i</text>'
                )
                y_offset += 60

            # Title
            title_color = tc.title_color
            if cfg.style in (OGImageStyle.GRADIENT, OGImageStyle.DARK):
                title_color = "#ffffff"

            svg_parts.append(
                f'<text x="{text_x}" y="{y_offset}" text-anchor="{text_anchor}" '
                f'fill="{title_color}" font-size="{tc.title_size}" font-weight="{tc.title_weight}" '
                f'font-family="{tc.font_family}">{self._escape_xml(title)}</text>'
            )
            y_offset += tc.title_size + 16

            # Description
            if description:
                desc_color = tc.description_color
                if cfg.style in (OGImageStyle.GRADIENT, OGImageStyle.DARK):
                    desc_color = "rgba(255,255,255,0.8)"

                svg_parts.append(
                    f'<text x="{text_x}" y="{y_offset}" text-anchor="{text_anchor}" '
                    f'fill="{desc_color}" font-size="{tc.description_size}" '
                    f'font-family="{tc.font_family}">{self._escape_xml(description)}</text>'
                )
                y_offset += tc.description_size + 20

            # Tags
            if cfg.include_tags and tags:
                tag_color = "rgba(255,255,255,0.6)"
                tag_y = y_offset
                for i, tag in enumerate(tags[:5]):
                    tag_x = text_x + (i - len(tags) // 2) * 120 if layout == OGImageLayout.CENTER else text_x
                    svg_parts.append(
                        f'<rect x="{tag_x - 40}" y="{tag_y - 16}" width="80" height="24" '
                        f'rx="12" ry="12" fill="rgba(255,255,255,0.15)"/>'
                    )
                    svg_parts.append(
                        f'<text x="{tag_x}" y="{tag_y}" text-anchor="middle" '
                        f'fill="{tag_color}" font-size="14" font-family="{tc.font_family}">'
                        f'#{self._escape_xml(tag)}</text>'
                    )
                y_offset += 30

            # Domain
            if cfg.include_domain:
                domain_color = tc.domain_color
                if cfg.style in (OGImageStyle.GRADIENT, OGImageStyle.DARK):
                    domain_color = "rgba(255,255,255,0.5)"

                domain_y = height - padding + 6
                svg_parts.append(
                    f'<text x="{text_x}" y="{domain_y}" text-anchor="{text_anchor}" '
                    f'fill="{domain_color}" font-size="{tc.domain_size}" '
                    f'font-family="{tc.font_family}">{self._escape_xml(domain)}</text>'
                )

            # Watermark
            if cfg.watermark and cfg.watermark.text:
                wm = cfg.watermark
                wm_x = width - padding - 10 if "right" in wm.position else padding + 10
                wm_y = height - padding + 6
                svg_parts.append(
                    f'<text x="{wm_x}" y="{wm_y}" text-anchor="end" '
                    f'fill="{wm.color}" font-size="{wm.font_size}" opacity="{wm.opacity}" '
                    f'font-family="{tc.font_family}">{self._escape_xml(wm.text)}</text>'
                )

            svg_parts.append("</svg>")
            svg_content = "\n".join(svg_parts)

            result = OGImageResult(
                url=url,
                status=OGImageStatus.READY,
                svg_content=svg_content,
                width=width,
                height=height,
                style=cfg.style,
                cache_key=cache_key,
            )
            self._cache[cache_key] = result
            return svg_content

        except Exception as e:
            result = OGImageResult(
                url=url,
                status=OGImageStatus.FAILED,
                error=str(e),
                style=cfg.style,
                cache_key=cache_key,
            )
            self._cache[cache_key] = result
            return ""

    def get_cached(self, url: str, config: Optional[OGImageConfig] = None) -> Optional[OGImageResult]:
        """Get a cached result."""
        cache_key = self._compute_cache_key(url, config)
        return self._cache.get(cache_key)

    def clear_cache(self) -> int:
        """Clear the cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


class OGImageManager:
    """Manage OG image generation and storage."""

    def __init__(self, config: Optional[OGImageConfig] = None) -> None:
        self.config = config or OGImageConfig()
        self.generator = OGImageGenerator(self.config)
        self._images: dict[str, OGImageResult] = {}

    def create_image(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        config: Optional[OGImageConfig] = None,
    ) -> OGImageResult:
        """Create an OG image."""
        cfg = config or self.config
        cache_key = self.generator._compute_cache_key(url, cfg)

        if cache_key in self.generator._cache:
            cached = self.generator._cache[cache_key]
            cached.status = OGImageStatus.CACHED
            self._images[url] = cached
            return cached

        try:
            svg = self.generator.generate(
                url, title, description, domain, favicon_url, tags, cfg
            )
            result = OGImageResult(
                url=url,
                status=OGImageStatus.READY if svg else OGImageStatus.FAILED,
                svg_content=svg if svg else None,
                width=cfg.size.width,
                height=cfg.size.height,
                style=cfg.style,
                cache_key=cache_key,
            )
            self._images[url] = result
            return result
        except Exception as e:
            result = OGImageResult(
                url=url,
                status=OGImageStatus.FAILED,
                error=str(e),
                style=cfg.style,
                cache_key=cache_key,
            )
            self._images[url] = result
            return result

    def create_image_batch(self, items: list[dict]) -> list[OGImageResult]:
        """Create images for multiple items."""
        results = []
        for item in items:
            result = self.create_image(
                url=item.get("url", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                domain=item.get("domain", ""),
                favicon_url=item.get("favicon_url"),
                tags=item.get("tags"),
            )
            results.append(result)
        return results

    def get_image(self, url: str) -> Optional[OGImageResult]:
        """Get an image by URL."""
        return self._images.get(url)

    def get_summary(self) -> dict:
        """Get a summary of images."""
        ready = sum(1 for img in self._images.values() if img.is_ready())
        failed = sum(1 for img in self._images.values() if img.is_failed())
        return {
            "total": len(self._images),
            "ready": ready,
            "failed": failed,
        }

    def clear_cache(self) -> int:
        """Clear the cache."""
        count = len(self._images)
        self._images.clear()
        self.generator.clear_cache()
        return count


class OGImageEngine:
    """High-level engine for OG image operations."""

    def __init__(self, config: Optional[OGImageConfig] = None) -> None:
        self.config = config or OGImageConfig()
        self.manager = OGImageManager(self.config)
        self.generator = OGImageGenerator(self.config)

    def generate(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        style: Optional[OGImageStyle] = None,
        layout: Optional[OGImageLayout] = None,
    ) -> OGImageResult:
        """Generate an OG image."""
        cfg = OGImageConfig(
            size=self.config.size,
            style=style or self.config.style,
            layout=layout or self.config.layout,
            background=self.config.background,
            text_config=self.config.text_config,
            watermark=self.config.watermark,
            max_title_length=self.config.max_title_length,
            max_description_length=self.config.max_description_length,
            include_domain=self.config.include_domain,
            include_favicon=self.config.include_favicon,
            include_tags=self.config.include_tags,
            border_radius=self.config.border_radius,
            padding=self.config.padding,
        )
        return self.manager.create_image(
            url, title, description, domain, favicon_url, tags, cfg
        )

    def generate_batch(self, items: list[dict]) -> list[OGImageResult]:
        """Generate images for multiple items."""
        return self.manager.create_image_batch(items)

    def get_svg(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        style: Optional[OGImageStyle] = None,
        layout: Optional[OGImageLayout] = None,
    ) -> str:
        """Get SVG content directly."""
        cfg = OGImageConfig(
            size=self.config.size,
            style=style or self.config.style,
            layout=layout or self.config.layout,
            background=self.config.background,
            text_config=self.config.text_config,
            watermark=self.config.watermark,
            max_title_length=self.config.max_title_length,
            max_description_length=self.config.max_description_length,
            include_domain=self.config.include_domain,
            include_favicon=self.config.include_favicon,
            include_tags=self.config.include_tags,
            border_radius=self.config.border_radius,
            padding=self.config.padding,
        )
        return self.generator.generate(
            url, title, description, domain, favicon_url, tags, cfg
        )

    def get_cached(self, url: str) -> Optional[OGImageResult]:
        """Get a cached image."""
        return self.manager.get_image(url)

    def get_summary(self) -> dict:
        """Get a summary."""
        return self.manager.get_summary()

    def clear_cache(self) -> int:
        """Clear the cache."""
        return self.manager.clear_cache()
