"""Content mobile module - mobile-responsive views and optimization."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class MobileBreakpoint(str, Enum):
    """CSS breakpoint definitions for responsive design."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"

    @property
    def max_width(self) -> int:
        widths = {
            MobileBreakpoint.SMALL: 640,
            MobileBreakpoint.MEDIUM: 768,
            MobileBreakpoint.LARGE: 1024,
            MobileBreakpoint.XLARGE: 1920,
        }
        return widths[self]

    @property
    def min_width(self) -> int:
        widths = {
            MobileBreakpoint.SMALL: 0,
            MobileBreakpoint.MEDIUM: 641,
            MobileBreakpoint.LARGE: 769,
            MobileBreakpoint.XLARGE: 1025,
        }
        return widths[self]

    def matches(self, width: int) -> bool:
        """Check if a given width falls within this breakpoint."""
        return self.min_width <= width <= self.max_width

    @classmethod
    def from_width(cls, width: int) -> "MobileBreakpoint":
        """Get the breakpoint for a given width."""
        for bp in [cls.SMALL, cls.MEDIUM, cls.LARGE, cls.XLARGE]:
            if width <= bp.max_width:
                return bp
        return cls.XLARGE

    def css_query(self) -> str:
        """Generate CSS media query for this breakpoint."""
        if self == MobileBreakpoint.SMALL:
            return f"@media (max-width: {self.max_width}px)"
        elif self == MobileBreakpoint.XLARGE:
            return f"@media (min-width: {self.min_width}px)"
        else:
            return f"@media (min-width: {self.min_width}px) and (max-width: {self.max_width}px)"


class MobileLayout(str, Enum):
    """Layout modes for mobile views."""

    LIST = "list"
    GRID = "grid"
    CARD = "card"
    COMPACT = "compact"
    FULLSCREEN = "fullscreen"

    @property
    def columns(self) -> int:
        cols = {
            MobileLayout.LIST: 1,
            MobileLayout.GRID: 2,
            MobileLayout.CARD: 1,
            MobileLayout.COMPACT: 3,
            MobileLayout.FULLSCREEN: 1,
        }
        return cols[self]

    def is_single_column(self) -> bool:
        """Check if this layout uses a single column."""
        return self.columns == 1

    @classmethod
    def default_for(cls, breakpoint: MobileBreakpoint) -> "MobileLayout":
        """Get the default layout for a breakpoint."""
        if breakpoint == MobileBreakpoint.SMALL:
            return cls.LIST
        return cls.GRID


class MobileTheme(str, Enum):
    """Theme modes for mobile views."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    def css_variable(self) -> str:
        """Generate CSS variable for this theme."""
        return f"--theme: {self.value};"

    def is_dark(self) -> bool:
        """Check if this is a dark theme."""
        return self == MobileTheme.DARK

    def contrast_ratio(self) -> float:
        """Get the contrast ratio for this theme."""
        return 4.5 if self == MobileTheme.LIGHT else 7.0

    def css_class(self) -> str:
        """Get the CSS class for this theme."""
        return f"theme-{self.value}"


@dataclass
class MobileViewport:
    """Represents a mobile viewport configuration."""

    width: int
    height: int
    device_pixel_ratio: float = 1.0

    @property
    def orientation(self) -> str:
        return "landscape" if self.width > self.height else "portrait"

    @property
    def css_width(self) -> int:
        return self.width

    @property
    def css_height(self) -> int:
        return self.height

    @property
    def physical_width(self) -> int:
        return int(self.width * self.device_pixel_ratio)

    @property
    def physical_height(self) -> int:
        return int(self.height * self.device_pixel_ratio)

    def __repr__(self) -> str:
        return f"MobileViewport(width={self.width}, height={self.height}, dpr={self.device_pixel_ratio})"

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "device_pixel_ratio": self.device_pixel_ratio,
            "orientation": self.orientation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MobileViewport":
        return cls(
            width=data.get("width", 375),
            height=data.get("height", 480),
            device_pixel_ratio=data.get("device_pixel_ratio", 1.0),
        )

    def rotate(self) -> None:
        """Rotate the viewport orientation."""
        self.width, self.height = self.height, self.width

    def is_mobile(self) -> bool:
        """Check if this viewport is mobile-sized."""
        return self.width <= 640

    def is_tablet(self) -> bool:
        """Check if this viewport is tablet-sized."""
        return 641 <= self.width <= 1024

    def is_desktop(self) -> bool:
        """Check if this viewport is desktop-sized."""
        return self.width > 1024

    def get_breakpoint(self) -> MobileBreakpoint:
        """Get the breakpoint for this viewport."""
        return MobileBreakpoint.from_width(self.width)

    def css_media_query(self) -> str:
        """Generate a CSS media query for this viewport."""
        return f"@media (max-width: {self.width}px)"


@dataclass
class MobilePreferences:
    """User preferences for mobile views."""

    theme: MobileTheme = MobileTheme.SYSTEM
    layout: MobileLayout = MobileLayout.LIST
    font_size: int = 16
    reduced_motion: bool = False
    high_contrast: bool = False

    def __repr__(self) -> str:
        return f"MobilePreferences(theme={self.theme.value}, layout={self.layout.value}, font_size={self.font_size})"

    def to_dict(self) -> dict:
        return {
            "theme": self.theme.value,
            "layout": self.layout.value,
            "font_size": self.font_size,
            "reduced_motion": self.reduced_motion,
            "high_contrast": self.high_contrast,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MobilePreferences":
        return cls(
            theme=MobileTheme(data.get("theme", "system")),
            layout=MobileLayout(data.get("layout", "list")),
            font_size=data.get("font_size", 16),
            reduced_motion=data.get("reduced_motion", False),
            high_contrast=data.get("high_contrast", False),
        )

    def css_custom_properties(self) -> str:
        """Generate CSS custom properties from preferences."""
        props = []
        props.append(f"--theme: {self.theme.value};")
        props.append(f"--font-size: {self.font_size}px;")
        if self.reduced_motion:
            props.append("--prefers-reduced-motion: reduce;")
        if self.high_contrast:
            props.append("--high-contrast: 1;")
        return "\n  ".join(props)

    def update(self, **kwargs: Any) -> None:
        """Update preferences with given keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def merge(self, other: "MobilePreferences") -> "MobilePreferences":
        """Merge with another preferences object, other takes precedence for non-default values."""
        merged = MobilePreferences(
            theme=other.theme if other.theme != MobileTheme.SYSTEM else self.theme,
            layout=other.layout if other.layout != MobileLayout.LIST else self.layout,
            font_size=other.font_size if other.font_size != 16 else self.font_size,
            reduced_motion=other.reduced_motion or self.reduced_motion,
            high_contrast=other.high_contrast or self.high_contrast,
        )
        return merged


@dataclass
class MobileViewConfig:
    """Configuration for a mobile view."""

    viewport: MobileViewport
    layout: MobileLayout = MobileLayout.LIST
    theme: MobileTheme = MobileTheme.SYSTEM
    font_size: int = 16
    reduced_motion: bool = False

    def to_dict(self) -> dict:
        return {
            "viewport": self.viewport.to_dict(),
            "layout": self.layout.value,
            "theme": self.theme.value,
            "font_size": self.font_size,
            "reduced_motion": self.reduced_motion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MobileViewConfig":
        viewport_data = data.get("viewport", {"width": 375, "height": 667})
        return cls(
            viewport=MobileViewport.from_dict(viewport_data),
            layout=MobileLayout(data.get("layout", "list")),
            theme=MobileTheme(data.get("theme", "system")),
            font_size=data.get("font_size", 16),
            reduced_motion=data.get("reduced_motion", False),
        )

    def generate_css(self) -> str:
        """Generate CSS for this view configuration."""
        prefs = MobilePreferences(
            theme=self.theme,
            layout=self.layout,
            font_size=self.font_size,
            reduced_motion=self.reduced_motion,
        )
        css = f"""
:root {{
  {prefs.css_custom_properties()}
}}

body {{
  font-size: {self.font_size}px;
  max-width: {self.viewport.width}px;
  margin: 0 auto;
}}
"""
        if self.layout == MobileLayout.GRID:
            css += """
.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
"""
        elif self.layout == MobileLayout.COMPACT:
            css += """
.content-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
"""
        return css

    def generate_html_head(self) -> str:
        """Generate HTML head elements for mobile optimization."""
        head = f"""<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
"""
        if self.theme == MobileTheme.DARK:
            head += '<meta name="color-scheme" content="dark">\n'
        elif self.theme == MobileTheme.LIGHT:
            head += '<meta name="color-scheme" content="light">\n'
        else:
            head += '<meta name="color-scheme" content="light dark">\n'
        return head

    def is_mobile_optimized(self) -> bool:
        """Check if this config is optimized for mobile."""
        return self.viewport.is_mobile()

    def get_breakpoint(self) -> MobileBreakpoint:
        """Get the breakpoint for this config."""
        return self.viewport.get_breakpoint()

    def get_default_layout(self) -> MobileLayout:
        """Get the default layout for the current breakpoint."""
        return MobileLayout.default_for(self.get_breakpoint())


class MobileOptimizationLevel(str, Enum):
    """Levels of mobile optimization."""

    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    FULL = "full"

    @property
    def priority(self) -> int:
        priorities = {
            MobileOptimizationLevel.NONE: 0,
            MobileOptimizationLevel.BASIC: 1,
            MobileOptimizationLevel.ADVANCED: 2,
            MobileOptimizationLevel.FULL: 3,
        }
        return priorities[self]

    def __gt__(self, other: "MobileOptimizationLevel") -> bool:
        return self.priority > other.priority

    def __lt__(self, other: "MobileOptimizationLevel") -> bool:
        return self.priority < other.priority

    @classmethod
    def from_string(cls, value: str) -> "MobileOptimizationLevel":
        try:
            return cls(value)
        except ValueError:
            return cls.NONE


@dataclass
class MobileOptimizationResult:
    """Result of mobile optimization."""

    original_size: int
    optimized_size: int
    level: MobileOptimizationLevel
    optimizations_applied: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def reduction_percent(self) -> float:
        if self.original_size == 0:
            return 0.0
        return round((1 - self.optimized_size / self.original_size) * 100, 1)

    def __repr__(self) -> str:
        return f"MobileOptimizationResult(reduction={self.reduction_percent}%, level={self.level.value})"

    def to_dict(self) -> dict:
        return {
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "level": self.level.value,
            "reduction_percent": self.reduction_percent,
            "optimizations_applied": self.optimizations_applied,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MobileOptimizationResult":
        return cls(
            original_size=data["original_size"],
            optimized_size=data["optimized_size"],
            level=MobileOptimizationLevel(data.get("level", "none")),
            optimizations_applied=data.get("optimizations_applied", []),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )

    def add_optimization(self, name: str) -> None:
        """Record an optimization that was applied."""
        if name not in self.optimizations_applied:
            self.optimizations_applied.append(name)


class MobileStore:
    """Stores mobile preferences, view configs, and optimization results."""

    def __init__(self) -> None:
        self._preferences: Dict[str, MobilePreferences] = {}
        self._view_configs: Dict[str, MobileViewConfig] = {}
        self._optimization_results: Dict[str, MobileOptimizationResult] = {}

    def set_preferences(self, user_id: str, prefs: MobilePreferences) -> None:
        self._preferences[user_id] = prefs

    def get_preferences(
        self, user_id: str, default: Optional[MobilePreferences] = None
    ) -> Optional[MobilePreferences]:
        if user_id in self._preferences:
            return self._preferences[user_id]
        return default

    def set_view_config(self, user_id: str, config: MobileViewConfig) -> None:
        self._view_configs[user_id] = config

    def get_view_config(self, user_id: str) -> Optional[MobileViewConfig]:
        return self._view_configs.get(user_id)

    def list_users(self) -> List[str]:
        return list(self._preferences.keys())

    def delete_user(self, user_id: str) -> None:
        self._preferences.pop(user_id, None)
        self._view_configs.pop(user_id, None)

    def set_optimization_result(
        self, page_id: str, result: MobileOptimizationResult
    ) -> None:
        self._optimization_results[page_id] = result

    def get_optimization_result(
        self, page_id: str
    ) -> Optional[MobileOptimizationResult]:
        return self._optimization_results.get(page_id)

    def list_optimization_results(self) -> List[MobileOptimizationResult]:
        return list(self._optimization_results.values())

    def clear_optimization_results(self) -> None:
        self._optimization_results.clear()

    def get_stats(self) -> dict:
        return {
            "total_users": len(self._preferences),
            "total_view_configs": len(self._view_configs),
            "total_optimization_results": len(self._optimization_results),
        }

    def serialize(self) -> dict:
        return {
            uid: prefs.to_dict() for uid, prefs in self._preferences.items()
        }

    def deserialize(self, data: dict) -> None:
        self.clear()
        for uid, prefs_data in data.items():
            self._preferences[uid] = MobilePreferences.from_dict(prefs_data)

    def clear(self) -> None:
        self._preferences.clear()
        self._view_configs.clear()
        self._optimization_results.clear()

    def get_or_create_preferences(self, user_id: str) -> MobilePreferences:
        if user_id in self._preferences:
            return self._preferences[user_id]
        prefs = MobilePreferences()
        self._preferences[user_id] = prefs
        return prefs

    def update_preferences(self, user_id: str, **kwargs: Any) -> None:
        if user_id in self._preferences:
            self._preferences[user_id].update(**kwargs)

    def detect_device(self, user_agent: str) -> dict:
        """Detect device type from user agent string."""
        is_mobile = bool(re.search(r"(iPhone|Android|Mobile|BlackBerry|IEMobile|Opera Mini)", user_agent, re.I))
        is_tablet = bool(re.search(r"(iPad|Tablet|Nexus 7)", user_agent, re.I))
        is_ios = bool(re.search(r"(iPhone|iPad|iPod)", user_agent, re.I))
        is_android = bool(re.search(r"Android", user_agent, re.I))
        return {
            "is_mobile": is_mobile and not is_tablet,
            "is_tablet": is_tablet,
            "is_desktop": not is_mobile and not is_tablet,
            "is_ios": is_ios,
            "is_android": is_android,
        }

    def generate_meta_tags(
        self,
        title: str,
        description: str,
        theme_color: str = "#ffffff",
    ) -> str:
        """Generate mobile meta tags."""
        tags = f"""<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="{theme_color}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="format-detection" content="telephone=no">
<title>{title}</title>
<meta name="description" content="{description}">
"""
        return tags

    def generate_og_tags(
        self, title: str, url: str, description: str, image: str = ""
    ) -> str:
        """Generate Open Graph meta tags."""
        tags = f"""<meta property="og:title" content="{title}">
<meta property="og:url" content="{url}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
"""
        if image:
            tags += f'<meta property="og:image" content="{image}">\n'
        return tags

    def generate_twitter_tags(
        self, title: str, image: str, description: str = ""
    ) -> str:
        """Generate Twitter card meta tags."""
        tags = f"""<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:image" content="{image}">
"""
        if description:
            tags += f'<meta name="twitter:description" content="{description}">\n'
        return tags
