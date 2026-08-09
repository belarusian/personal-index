"""Content dashboard for personal-index.

Provides dashboard widgets, configuration, and stats display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DashboardWidgetType(str, Enum):
    """Types of dashboard widgets."""

    STAT = "stat"
    CHART = "chart"
    TABLE = "table"
    LIST = "list"
    SUMMARY = "summary"


@dataclass
class DashboardWidget:
    """A single widget on the dashboard."""

    widget_id: str
    widget_type: DashboardWidgetType
    title: str
    data: dict
    position: int = 0

    def to_dict(self) -> dict:
        """Convert widget to dictionary."""
        return {
            "widget_id": self.widget_id,
            "type": self.widget_type.value,
            "title": self.title,
            "data": self.data,
            "position": self.position,
        }


@dataclass
class DashboardConfig:
    """Configuration for the dashboard."""

    title: str = "Content Dashboard"
    max_widgets: int = 20
    refresh_interval_seconds: int = 60
    theme: str = "default"
    layout: str = "grid"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "max_widgets": self.max_widgets,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "theme": self.theme,
            "layout": self.layout,
        }


@dataclass
class DashboardStats:
    """Aggregated stats for the dashboard."""

    total_items: int = 0
    total_views: int = 0
    total_bookmarks: int = 0
    total_shares: int = 0
    avg_engagement: float = 0.0
    views_per_item: float = 0.0

    def __post_init__(self) -> None:
        if self.total_items > 0:
            self.views_per_item = self.total_views / self.total_items

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "total_views": self.total_views,
            "total_bookmarks": self.total_bookmarks,
            "total_shares": self.total_shares,
            "avg_engagement": round(self.avg_engagement, 2),
            "views_per_item": round(self.views_per_item, 2),
        }


class ContentDashboard:
    """Dashboard for displaying content statistics."""

    def __init__(self, config: Optional[DashboardConfig] = None) -> None:
        self.config = config or DashboardConfig()
        self._widgets: list[DashboardWidget] = []

    def add_widget(self, widget: DashboardWidget) -> None:
        """Add a widget to the dashboard."""
        if len(self._widgets) >= self.config.max_widgets:
            raise ValueError(
                f"Dashboard has reached max widgets ({self.config.max_widgets})"
            )
        widget.position = len(self._widgets)
        self._widgets.append(widget)

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget by ID. Returns True if removed."""
        for i, w in enumerate(self._widgets):
            if w.widget_id == widget_id:
                self._widgets.pop(i)
                # Re-index positions
                for j, w in enumerate(self._widgets):
                    w.position = j
                return True
        return False

    def get_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """Get a widget by ID."""
        for w in self._widgets:
            if w.widget_id == widget_id:
                return w
        return None

    def get_widgets(self) -> list[DashboardWidget]:
        """Get all widgets."""
        return list(self._widgets)

    def get_stats(self) -> DashboardStats:
        """Get aggregated dashboard stats."""
        total_items = 0
        total_views = 0
        total_bookmarks = 0
        total_shares = 0
        engagement_scores = []

        for w in self._widgets:
            data = w.data
            if isinstance(data, dict):
                total_items += data.get("total_items", 0)
                total_views += data.get("total_views", 0)
                total_bookmarks += data.get("total_bookmarks", 0)
                total_shares += data.get("total_shares", 0)
                if "avg_engagement" in data:
                    engagement_scores.append(data["avg_engagement"])

        avg_engagement = (
            sum(engagement_scores) / len(engagement_scores)
            if engagement_scores
            else 0.0
        )

        return DashboardStats(
            total_items=total_items,
            total_views=total_views,
            total_bookmarks=total_bookmarks,
            total_shares=total_shares,
            avg_engagement=avg_engagement,
        )

    def render(self) -> dict:
        """Render the full dashboard as a dictionary."""
        return {
            "config": self.config.to_dict(),
            "widgets": [w.to_dict() for w in self._widgets],
            "stats": self.get_stats().to_dict(),
        }

    def clear_widgets(self) -> None:
        """Remove all widgets."""
        self._widgets.clear()
