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


class TestContentDashboard:
    def test_create_dashboard(self):
        dashboard = ContentDashboard()
        assert dashboard.config.title == "Content Dashboard"
        assert len(dashboard.get_widgets()) == 0

    def test_add_widget(self):
        dashboard = ContentDashboard()
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test",
            data={"count": 10},
        )
        dashboard.add_widget(w)
        assert len(dashboard.get_widgets()) == 1

    def test_add_widget_auto_position(self):
        dashboard = ContentDashboard()
        w1 = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test 1",
            data={},
        )
        w2 = DashboardWidget(
            widget_id="w2",
            widget_type=DashboardWidgetType.STAT,
            title="Test 2",
            data={},
        )
        dashboard.add_widget(w1)
        dashboard.add_widget(w2)
        assert w1.position == 0
        assert w2.position == 1

    def test_remove_widget(self):
        dashboard = ContentDashboard()
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test",
            data={},
        )
        dashboard.add_widget(w)
        assert dashboard.remove_widget("w1") is True
        assert len(dashboard.get_widgets()) == 0

    def test_remove_widget_not_found(self):
        dashboard = ContentDashboard()
        assert dashboard.remove_widget("nonexistent") is False

    def test_get_widget(self):
        dashboard = ContentDashboard()
        w = DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test",
            data={"count": 10},
        )
        dashboard.add_widget(w)
        result = dashboard.get_widget("w1")
        assert result is not None
        assert result.widget_id == "w1"

    def test_get_widget_not_found(self):
        dashboard = ContentDashboard()
        assert dashboard.get_widget("nonexistent") is None

    def test_max_widgets_limit(self):
        config = DashboardConfig(max_widgets=2)
        dashboard = ContentDashboard(config=config)
        dashboard.add_widget(DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="T1",
            data={},
        ))
        dashboard.add_widget(DashboardWidget(
            widget_id="w2",
            widget_type=DashboardWidgetType.STAT,
            title="T2",
            data={},
        ))
        with pytest.raises(ValueError, match="max widgets"):
            dashboard.add_widget(DashboardWidget(
                widget_id="w3",
                widget_type=DashboardWidgetType.STAT,
                title="T3",
                data={},
            ))

    def test_get_stats(self):
        dashboard = ContentDashboard()
        dashboard.add_widget(DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Stats",
            data={"total_items": 100, "total_views": 500, "total_bookmarks": 20},
        ))
        stats = dashboard.get_stats()
        assert stats.total_items == 100
        assert stats.total_views == 500
        assert stats.total_bookmarks == 20

    def test_render(self):
        dashboard = ContentDashboard()
        dashboard.add_widget(DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="Test",
            data={"count": 10},
        ))
        rendered = dashboard.render()
        assert "config" in rendered
        assert "widgets" in rendered
        assert "stats" in rendered
        assert len(rendered["widgets"]) == 1

    def test_clear_widgets(self):
        dashboard = ContentDashboard()
        dashboard.add_widget(DashboardWidget(
            widget_id="w1",
            widget_type=DashboardWidgetType.STAT,
            title="T1",
            data={},
        ))
        dashboard.clear_widgets()
        assert len(dashboard.get_widgets()) == 0

    def test_remove_widget_reindex(self):
        dashboard = ContentDashboard()
        for i in range(3):
            dashboard.add_widget(DashboardWidget(
                widget_id=f"w{i}",
                widget_type=DashboardWidgetType.STAT,
                title=f"T{i}",
                data={},
            ))
        dashboard.remove_widget("w1")
        widgets = dashboard.get_widgets()
        assert len(widgets) == 2
        assert widgets[0].position == 0
        assert widgets[1].position == 1
