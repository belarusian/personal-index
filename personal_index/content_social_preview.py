"""Content social preview module - generate social media preview cards."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class SocialPlatform:
    """Social platform configuration."""

    def __init__(
        self,
        value: str,
        max_title_length: int = 70,
        max_description_length: int = 200,
        image_width: int = 1200,
        image_height: int = 630,
    ) -> None:
        self.value = value
        self.max_title_length = max_title_length
        self.max_description_length = max_description_length
        self.image_width = image_width
        self.image_height = image_height

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SocialPlatform):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"SocialPlatform.{self.value.upper()}"


# Platform instances
_TWITTER = SocialPlatform("twitter", max_title_length=70, max_description_length=200, image_width=1200, image_height=628)
_FACEBOOK = SocialPlatform("facebook", max_title_length=60, max_description_length=110, image_width=1200, image_height=630)
_LINKEDIN = SocialPlatform("linkedin", max_title_length=200, max_description_length=300, image_width=1200, image_height=627)
_SLACK = SocialPlatform("slack", max_title_length=80, max_description_length=250, image_width=800, image_height=400)
_DISCORD = SocialPlatform("discord", max_title_length=80, max_description_length=250, image_width=800, image_height=400)
_TELEGRAM = SocialPlatform("telegram", max_title_length=64, max_description_length=256, image_width=1280, image_height=640)
_WHATSAPP = SocialPlatform("whatsapp", max_title_length=100, max_description_length=200, image_width=1200, image_height=630)
_GENERIC = SocialPlatform("generic", max_title_length=70, max_description_length=200, image_width=1200, image_height=630)

# Add as class attributes
SocialPlatform.TWITTER = _TWITTER
SocialPlatform.FACEBOOK = _FACEBOOK
SocialPlatform.LINKEDIN = _LINKEDIN
SocialPlatform.SLACK = _SLACK
SocialPlatform.DISCORD = _DISCORD
SocialPlatform.TELEGRAM = _TELEGRAM
SocialPlatform.WHATSAPP = _WHATSAPP
SocialPlatform.GENERIC = _GENERIC

# Keep module-level aliases for backward compatibility
TWITTER = SocialPlatform.TWITTER
FACEBOOK = SocialPlatform.FACEBOOK
LINKEDIN = SocialPlatform.LINKEDIN
SLACK = SocialPlatform.SLACK
DISCORD = SocialPlatform.DISCORD
TELEGRAM = SocialPlatform.TELEGRAM
WHATSAPP = SocialPlatform.WHATSAPP
GENERIC = SocialPlatform.GENERIC


class PreviewCardType(str, Enum):
    """Type of preview card."""

    SUMMARY = "summary"
    SUMMARY_LARGE_IMAGE = "summary_large_image"
    APP = "app"
    PLAYER = "player"


class PreviewCardSize:
    """Size configuration for preview cards."""

    _PRESETS = {
        "twitter_small": (280, 150),
        "twitter_large": (1200, 628),
        "facebook": (1200, 630),
        "linkedin": (1200, 627),
        "square": (1200, 1200),
    }

    def __init__(self, width: int = 1200, height: int = 630) -> None:
        self.width = width
        self.height = height

    def aspect_ratio(self) -> float:
        """Calculate the aspect ratio."""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PreviewCardSize):
            return self.width == other.width and self.height == other.height
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.width, self.height))


# Class-level preset instances
PreviewCardSize.TWITTER_SMALL = PreviewCardSize(280, 150)
PreviewCardSize.TWITTER_LARGE = PreviewCardSize(1200, 628)
PreviewCardSize.FACEBOOK = PreviewCardSize(1200, 630)
PreviewCardSize.LINKEDIN = PreviewCardSize(1200, 627)
PreviewCardSize.SQUARE = PreviewCardSize(1200, 1200)


class PreviewCardStyle(str, Enum):
    """Visual style for preview cards."""

    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    BOLD = "bold"
    DARK = "dark"


class SocialPreviewStatus(str, Enum):
    """Status of social preview generation."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class SocialPreviewConfig:
    """Configuration for social preview generation."""

    platform: SocialPlatform = GENERIC
    card_type: PreviewCardType = PreviewCardType.SUMMARY
    include_domain: bool = True
    include_favicon: bool = True
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    cache_ttl_seconds: int = 86400

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "platform": self.platform.value,
            "card_type": self.card_type.value,
            "include_domain": self.include_domain,
            "include_favicon": self.include_favicon,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocialPreviewConfig":
        """Deserialize from dictionary."""
        platform_value = data.get("platform", "generic")
        platform = GENERIC
        for p in [TWITTER, FACEBOOK, LINKEDIN, SLACK, DISCORD, TELEGRAM, WHATSAPP, GENERIC]:
            if p.value == platform_value:
                platform = p
                break

        card_type = data.get("card_type", "summary")
        if isinstance(card_type, str):
            card_type = PreviewCardType(card_type)

        return cls(
            platform=platform,
            card_type=card_type,
            include_domain=data.get("include_domain", True),
            include_favicon=data.get("include_favicon", True),
            background_color=data.get("background_color", "#ffffff"),
            text_color=data.get("text_color", "#333333"),
            cache_ttl_seconds=data.get("cache_ttl_seconds", 86400),
        )


@dataclass
class PreviewCardConfig:
    """Configuration for preview card generation."""

    size: PreviewCardSize = field(default_factory=lambda: PreviewCardSize(1200, 630))
    style: PreviewCardStyle = PreviewCardStyle.MODERN
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    font_family: str = "sans-serif"
    border_radius: int = 0
    padding: int = 20
    include_domain: bool = True
    include_favicon: bool = True
    max_title_length: int = 70
    max_description_length: int = 200

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "size": {"width": self.size.width, "height": self.size.height},
            "style": self.style.value,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "font_family": self.font_family,
            "border_radius": self.border_radius,
            "padding": self.padding,
            "include_domain": self.include_domain,
            "include_favicon": self.include_favicon,
            "max_title_length": self.max_title_length,
            "max_description_length": self.max_description_length,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreviewCardConfig":
        """Deserialize from dictionary."""
        size_data = data.get("size", {})
        size = PreviewCardSize(
            width=size_data.get("width", 1200),
            height=size_data.get("height", 630),
        )
        style = data.get("style", "modern")
        if isinstance(style, str):
            style = PreviewCardStyle(style)
        return cls(
            size=size,
            style=style,
            background_color=data.get("background_color", "#ffffff"),
            text_color=data.get("text_color", "#333333"),
            font_family=data.get("font_family", "sans-serif"),
            border_radius=data.get("border_radius", 0),
            padding=data.get("padding", 20),
            include_domain=data.get("include_domain", True),
            include_favicon=data.get("include_favicon", True),
            max_title_length=data.get("max_title_length", 70),
            max_description_length=data.get("max_description_length", 200),
        )


@dataclass
class PreviewCardTemplate:
    """Template for preview card generation."""

    style: PreviewCardStyle
    background_color: str
    text_color: str
    font_family: str
    border_radius: int
    has_gradient: bool = False
    gradient_colors: list[str] = field(default_factory=list)

    @classmethod
    def get_template(cls, style: str) -> "PreviewCardTemplate":
        """Get a template by style name."""
        templates = {
            PreviewCardStyle.MODERN: cls(
                style=PreviewCardStyle.MODERN,
                background_color="#ffffff",
                text_color="#333333",
                font_family="sans-serif",
                border_radius=8,
            ),
            PreviewCardStyle.CLASSIC: cls(
                style=PreviewCardStyle.CLASSIC,
                background_color="#f8f9fa",
                text_color="#212529",
                font_family="Georgia, serif",
                border_radius=0,
            ),
            PreviewCardStyle.MINIMAL: cls(
                style=PreviewCardStyle.MINIMAL,
                background_color="#ffffff",
                text_color="#000000",
                font_family="Helvetica, sans-serif",
                border_radius=0,
            ),
            PreviewCardStyle.BOLD: cls(
                style=PreviewCardStyle.BOLD,
                background_color="#000000",
                text_color="#ffffff",
                font_family="Arial Black, sans-serif",
                border_radius=0,
                has_gradient=True,
                gradient_colors=["#000000", "#333333"],
            ),
            PreviewCardStyle.DARK: cls(
                style=PreviewCardStyle.DARK,
                background_color="#1a1a2e",
                text_color="#eaeaea",
                font_family="sans-serif",
                border_radius=8,
                has_gradient=True,
                gradient_colors=["#1a1a2e", "#16213e"],
            ),
        }
        try:
            style_enum = PreviewCardStyle(style)
            return templates.get(style_enum, templates[PreviewCardStyle.MODERN])
        except ValueError:
            return templates[PreviewCardStyle.MODERN]


@dataclass
class PreviewCardResult:
    """Result of preview card generation."""

    url: str
    status: SocialPreviewStatus = SocialPreviewStatus.PENDING
    svg_content: Optional[str] = None
    width: int = 0
    height: int = 0
    style: PreviewCardStyle = PreviewCardStyle.MODERN
    error: Optional[str] = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cache_key: str = ""

    def is_ready(self) -> bool:
        """Check if the card is ready."""
        return self.status in (SocialPreviewStatus.READY, SocialPreviewStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if generation failed."""
        return self.status == SocialPreviewStatus.FAILED

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
    def from_dict(cls, data: dict) -> "PreviewCardResult":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = SocialPreviewStatus(status)
        style = data.get("style", "modern")
        if isinstance(style, str):
            style = PreviewCardStyle(style)
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


@dataclass
class SocialPreviewResult:
    """Result of social preview generation."""

    url: str
    platform: SocialPlatform = GENERIC
    status: SocialPreviewStatus = SocialPreviewStatus.PENDING
    og_title: str = ""
    og_description: str = ""
    og_image_url: Optional[str] = None
    og_type: str = ""
    twitter_card: str = ""
    twitter_image_url: Optional[str] = None
    card_svg: Optional[str] = None
    error: Optional[str] = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_ready(self) -> bool:
        """Check if the preview is ready."""
        return self.status in (SocialPreviewStatus.READY, SocialPreviewStatus.CACHED)

    def is_failed(self) -> bool:
        """Check if generation failed."""
        return self.status == SocialPreviewStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "platform": self.platform.value,
            "status": self.status.value,
            "og_title": self.og_title,
            "og_description": self.og_description,
            "og_image_url": self.og_image_url,
            "og_type": self.og_type,
            "twitter_card": self.twitter_card,
            "twitter_image_url": self.twitter_image_url,
            "card_svg": self.card_svg,
            "error": self.error,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocialPreviewResult":
        """Deserialize from dictionary."""
        platform_value = data.get("platform", "generic")
        platform = GENERIC
        for p in [TWITTER, FACEBOOK, LINKEDIN, SLACK, DISCORD, TELEGRAM, WHATSAPP, GENERIC]:
            if p.value == platform_value:
                platform = p
                break

        status = data.get("status", "pending")
        if isinstance(status, str):
            status = SocialPreviewStatus(status)

        return cls(
            url=data.get("url", ""),
            platform=platform,
            status=status,
            og_title=data.get("og_title", ""),
            og_description=data.get("og_description", ""),
            og_image_url=data.get("og_image_url"),
            og_type=data.get("og_type", ""),
            twitter_card=data.get("twitter_card", ""),
            twitter_image_url=data.get("twitter_image_url"),
            card_svg=data.get("card_svg"),
            error=data.get("error"),
            generated_at=data.get("generated_at", datetime.now(timezone.utc).isoformat()),
        )


class PreviewCardGenerator:
    """Generate SVG preview cards."""

    def __init__(self, config: Optional[PreviewCardConfig] = None) -> None:
        self.config = config or PreviewCardConfig()
        self._cache: dict[str, PreviewCardResult] = {}

    def _compute_cache_key(self, url: str, config: Optional[PreviewCardConfig] = None) -> str:
        """Compute a cache key."""
        cfg = config or self.config
        raw = f"{url}:{cfg.style.value}:{cfg.size.width}:{cfg.size.height}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def generate_card(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        image_url: Optional[str] = None,
        config: Optional[PreviewCardConfig] = None,
    ) -> str:
        """Generate an SVG preview card."""
        cfg = config or self.config
        template = PreviewCardTemplate.get_template(cfg.style.value)
        width = cfg.size.width
        height = cfg.size.height
        padding = cfg.padding

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

        # Defs for gradients
        if template.has_gradient and template.gradient_colors:
            svg_parts.append(
                f'<defs><linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">'
                f'<stop offset="0%" stop-color="{template.gradient_colors[0]}"/>'
                f'<stop offset="100%" stop-color="{template.gradient_colors[1]}"/>'
                f"</linearGradient></defs>"
            )
            bg_fill = "url(#cardBg)"
        else:
            bg_fill = template.background_color

        # Background
        rx = cfg.border_radius
        svg_parts.append(
            f'<rect width="{width}" height="{height}" rx="{rx}" ry="{rx}" fill="{bg_fill}"/>'
        )

        # Image area (top portion for summary_large_image)
        if image_url:
            img_height = height // 3
            svg_parts.append(
                f'<rect x="0" y="0" width="{width}" height="{img_height}" fill="#cccccc"/>'
            )
            svg_parts.append(
                f'<text x="{width // 2}" y="{img_height // 2}" text-anchor="middle" '
                f'fill="#666666" font-size="14" font-family="{cfg.font_family}">'
                f'[Image: {image_url}]</text>'
            )
            text_y_start = img_height + padding
        else:
            text_y_start = padding

        # Favicon
        if cfg.include_favicon and favicon_url:
            svg_parts.append(
                f'<image x="{padding + 4}" y="{text_y_start + 4}" width="24" height="24" href="{favicon_url}"/>'
            )
            svg_parts.append(
                f'<circle cx="{padding + 16}" cy="{text_y_start + 16}" r="12" fill="#dddddd"/>'
            )
            svg_parts.append(
                f'<text x="{padding + 16}" y="{text_y_start + 20}" text-anchor="middle" '
                f'fill="#666666" font-size="8" font-family="{cfg.font_family}">i</text>'
            )

        # Title
        title_x = padding + (40 if (cfg.include_favicon and favicon_url) else 0)
        svg_parts.append(
            f'<text x="{title_x}" y="{text_y_start + 20}" '
            f'fill="{template.text_color}" font-size="24" font-weight="bold" '
            f'font-family="{cfg.font_family}">{title}</text>'
        )

        # Description
        desc_y = text_y_start + 50
        if description:
            svg_parts.append(
                f'<text x="{title_x}" y="{desc_y}" '
                f'fill="{template.text_color}" font-size="16" '
                f'font-family="{cfg.font_family}">{description}</text>'
            )

        # Domain
        if cfg.include_domain:
            domain_y = height - padding - 10
            svg_parts.append(
                f'<text x="{width - padding}" y="{domain_y}" text-anchor="end" '
                f'fill="{template.text_color}" font-size="12" opacity="0.6" '
                f'font-family="{cfg.font_family}">{domain}</text>'
            )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def get_cached(self, url: str, config: Optional[PreviewCardConfig] = None) -> Optional[PreviewCardResult]:
        """Get a cached card result."""
        cache_key = self._compute_cache_key(url, config)
        return self._cache.get(cache_key)

    def clear_cache(self) -> int:
        """Clear the cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


class PreviewCardManager:
    """Manage preview card generation and storage."""

    def __init__(self, config: Optional[PreviewCardConfig] = None) -> None:
        self.config = config or PreviewCardConfig()
        self.generator = PreviewCardGenerator(self.config)
        self._cards: dict[str, PreviewCardResult] = {}

    def create_card(
        self,
        url: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        favicon_url: Optional[str] = None,
        image_url: Optional[str] = None,
        config: Optional[PreviewCardConfig] = None,
    ) -> PreviewCardResult:
        """Create a preview card."""
        cfg = config or self.config
        cache_key = self.generator._compute_cache_key(url, cfg)

        if cache_key in self.generator._cache:
            cached = self.generator._cache[cache_key]
            cached.status = SocialPreviewStatus.CACHED
            self._cards[url] = cached
            return cached

        try:
            svg = self.generator.generate_card(
                url, title, description, domain, favicon_url, image_url, cfg
            )
            result = PreviewCardResult(
                url=url,
                status=SocialPreviewStatus.READY,
                svg_content=svg,
                width=cfg.size.width,
                height=cfg.size.height,
                style=cfg.style,
                cache_key=cache_key,
            )
            self.generator._cache[cache_key] = result
            self._cards[url] = result
            return result
        except Exception as e:
            result = PreviewCardResult(
                url=url,
                status=SocialPreviewStatus.FAILED,
                error=str(e),
                style=cfg.style,
                cache_key=cache_key,
            )
            self._cards[url] = result
            return result

    def create_card_batch(self, items: list[dict]) -> list[PreviewCardResult]:
        """Create cards for multiple items."""
        results = []
        for item in items:
            result = self.create_card(
                url=item.get("url", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                domain=item.get("domain", ""),
                favicon_url=item.get("favicon_url"),
                image_url=item.get("image_url"),
            )
            results.append(result)
        return results

    def get_card(self, url: str) -> Optional[PreviewCardResult]:
        """Get a card by URL."""
        return self._cards.get(url)

    def get_summary(self) -> dict:
        """Get a summary of cards."""
        ready = sum(1 for c in self._cards.values() if c.is_ready())
        failed = sum(1 for c in self._cards.values() if c.is_failed())
        return {
            "total": len(self._cards),
            "ready": ready,
            "failed": failed,
        }


class SocialPreviewEngine:
    """High-level engine for social preview generation."""

    def __init__(self, config: Optional[SocialPreviewConfig] = None) -> None:
        self.config = config or SocialPreviewConfig()
        self.card_manager = PreviewCardManager()
        self._previews: dict[str, SocialPreviewResult] = {}

    def generate_preview(
        self,
        url: str,
        title: str = "",
        description: str = "",
        image_url: Optional[str] = None,
        platform: Optional[SocialPlatform] = None,
        og_type: str = "",
        twitter_card: str = "",
    ) -> SocialPreviewResult:
        """Generate a social preview for a URL."""
        plat = platform or self.config.platform

        # Check cache
        cached = self._previews.get(url)
        if cached:
            cached.status = SocialPreviewStatus.CACHED
            return cached

        # Generate card
        card_config = PreviewCardConfig(
            size=PreviewCardSize(plat.image_width, plat.image_height),
            style=PreviewCardStyle.MODERN,
            background_color=self.config.background_color,
            text_color=self.config.text_color,
            max_title_length=plat.max_title_length,
            max_description_length=plat.max_description_length,
        )

        card_result = self.card_manager.create_card(
            url=url,
            title=title,
            description=description,
            image_url=image_url,
            config=card_config,
        )

        result = SocialPreviewResult(
            url=url,
            platform=plat,
            status=SocialPreviewStatus.READY if card_result.is_ready() else SocialPreviewStatus.FAILED,
            og_title=title,
            og_description=description,
            og_image_url=image_url,
            og_type=og_type,
            twitter_card=twitter_card,
            twitter_image_url=image_url,
            card_svg=card_result.svg_content,
        )
        self._previews[url] = result
        return result

    def generate_card(
        self,
        url: str,
        title: str = "",
        domain: str = "",
        description: str = "",
        image_url: Optional[str] = None,
        favicon_url: Optional[str] = None,
        style: PreviewCardStyle = PreviewCardStyle.MODERN,
    ) -> str:
        """Generate a card SVG directly."""
        config = PreviewCardConfig(style=style)
        return self.card_manager.generator.generate_card(
            url, title, description, domain, favicon_url, image_url, config
        )

    def generate_card_batch(self, items: list[dict]) -> list[str]:
        """Generate card SVGs for multiple items."""
        svgs = []
        for item in items:
            svg = self.generate_card(
                url=item.get("url", ""),
                title=item.get("title", ""),
                domain=item.get("domain", ""),
                description=item.get("description", ""),
                image_url=item.get("image_url"),
                favicon_url=item.get("favicon_url"),
                style=item.get("style", PreviewCardStyle.MODERN),
            )
            svgs.append(svg)
        return svgs

    def get_cached(self, url: str) -> Optional[SocialPreviewResult]:
        """Get a cached preview."""
        return self._previews.get(url)

    def get_summary(self) -> dict:
        """Get a summary of previews."""
        return {
            "total": len(self._previews),
            "ready": sum(1 for p in self._previews.values() if p.is_ready()),
            "failed": sum(1 for p in self._previews.values() if p.is_failed()),
        }

    def clear_cache(self) -> int:
        """Clear the cache."""
        count = len(self._previews)
        self._previews.clear()
        self.card_manager.generator.clear_cache()
        return count
