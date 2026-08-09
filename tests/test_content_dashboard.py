"""Tests for content dashboard module."""

import pytest
from personal_index.content_dashboard import (
    DashboardWidget,
    DashboardWidgetType,
    ContentDashboard,
    DashboardConfig,
    DashboardStats,
)


class TestDashboardWidget:
    def test_create_widget(self):
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Total Items",
            data={"count": 100},
        )
        assert w.widget_id == "w1"
        assert w.widget_type == DashboardWidgetType.STAT
        assert w.title == "Total Items"
        assert w.data["count"] == 100

    def test_widget_default_position(self):
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test",
            data={},
        )
        assert w.position == 0

    def test_widget_to_dict(self):
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.CHART,
            title="Views Chart",
            data={"labels": ["Mon", "Tue"], "values": [10, 20]},
            position=1,
        )
        d = w.to_dict()
        assert d["widget_id"] == "w1"
        assert d["type"] == "chart"
        assert d["title"] == "Views Chart"
        assert d["position"] == 1


class TestDashboardWidgetType:
    def test_all_types_exist(self):
        assert DashboardWidgetType.STAT.value == "stat"
        assert DashboardWidgetType.CHART.value == "chart"
        assert DashboardWidgetType.TABLE.value == "table"
        assert DashboardWidgetType.LIST.value == "list"
        assert DashboardWidgetType.SUMMARY.value == "summary"


class TestDashboardConfig:
    def test_default_config(self):
        config = DashboardConfig()
        assert config.title == "Content Dashboard"
        assert config.max_widgets == 20
        assert config.refresh_interval_seconds == 60

    def test_custom_config(self):
        config = DashboardConfig(
            title="My Dashboard",
            max_widgets=10,
            refresh_interval_seconds=30,
        )
        assert config.title == "My Dashboard"
        assert config.max_widgets == 10
        assert config.refresh_interval_seconds == 30

    def test_config_to_dict(self):
        config = DashboardConfig(title="Test")
        d = config.to_dict()
        assert d["title"] == "Test"
        assert "max_widgets" in d


class TestDashboardStats:
    def test_default_stats(self):
        stats = DashboardStats()
        assert stats.total_items == 0
        assert stats.total_views == 0
        assert stats.total_bookmarks == 0
        assert stats.avg_engagement == 0.0

    def test_stats_with_values(self):
        stats = DashboardStats(
            total_items=100,
            total_views=5000,
            total_bookmarks=200,
            avg_engagement=15.5,
        )
        assert stats.total_items == 100
        assert stats.views_per_item == 50.0

    def test_stats_views_per_item_zero(self):
        stats = DashboardStats(total_items=0, total_views=100)
        assert stats.views_per_item == 0.0

    def test_stats_to_dict(self):
        stats = DashboardStats(total_items=50, total_views=1000)
        d = stats.to_dict()
        assert d["total_items"] == 50
        assert d["views_per_item"] == 20.0
