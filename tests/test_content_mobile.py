"""Tests for content_mobile module - mobile-responsive views."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_mobile import (
    MobileViewport,
    MobileBreakpoint,
    MobileLayout,
    MobileTheme,
    MobilePreferences,
    MobileViewConfig,
    MobileStore,
    MobileOptimizationResult,
    MobileOptimizationLevel,
)


class TestMobileViewport:
    """Tests for MobileViewport dataclass."""

    def test_create_viewport_default(self):
        vp = MobileViewport(width=375, height=667)
        assert vp.width == 375
        assert vp.height == 667
        assert vp.device_pixel_ratio == 1.0
        assert vp.orientation == "portrait"

    def test_create_viewport_landscape(self):
        vp = MobileViewport(width=1024, height=768)
        assert vp.orientation == "landscape"

    def test_create_viewport_with_dpr(self):
        vp = MobileViewport(width=375, height=667, device_pixel_ratio=3.0)
        assert vp.device_pixel_ratio == 3.0
        assert vp.css_width == 375
        assert vp.physical_width == 1125

    def test_viewport_to_dict(self):
        vp = MobileViewport(width=375, height=667, device_pixel_ratio=2.0)
        d = vp.to_dict()
        assert d["width"] == 375
        assert d["height"] == 667
        assert d["device_pixel_ratio"] == 2.0
        assert d["orientation"] == "portrait"

    def test_viewport_from_dict(self):
        data = {"width": 414, "height": 896, "device_pixel_ratio": 2.0}
        vp = MobileViewport.from_dict(data)
        assert vp.width == 414
        assert vp.height == 896
        assert vp.device_pixel_ratio == 2.0

    def test_viewport_rotate(self):
        vp = MobileViewport(width=375, height=667)
        vp.rotate()
        assert vp.width == 667
        assert vp.height == 375
        assert vp.orientation == "landscape"

    def test_viewport_rotate_back(self):
        vp = MobileViewport(width=667, height=375)
        vp.rotate()
        assert vp.width == 375
        assert vp.height == 667
        assert vp.orientation == "portrait"

    def test_viewport_is_mobile(self):
        vp = MobileViewport(width=375, height=667)
        assert vp.is_mobile() is True

    def test_viewport_is_tablet(self):
        vp = MobileViewport(width=768, height=1024)
        assert vp.is_tablet() is True

    def test_viewport_is_desktop(self):
        vp = MobileViewport(width=1920, height=1080)
        assert vp.is_desktop() is True

    def test_viewport_get_breakpoint(self):
        vp = MobileViewport(width=375, height=667)
        assert vp.get_breakpoint() == MobileBreakpoint.SMALL

    def test_viewport_get_breakpoint_medium(self):
        vp = MobileViewport(width=768, height=1024)
        assert vp.get_breakpoint() == MobileBreakpoint.MEDIUM

    def test_viewport_get_breakpoint_large(self):
        vp = MobileViewport(width=900, height=800)
        assert vp.get_breakpoint() == MobileBreakpoint.LARGE

    def test_viewport_get_breakpoint_xlarge(self):
        vp = MobileViewport(width=1920, height=1080)
        assert vp.get_breakpoint() == MobileBreakpoint.XLARGE

    def test_viewport_css_media_query(self):
        vp = MobileViewport(width=375, height=667)
        query = vp.css_media_query()
        assert "max-width" in query
        assert "375px" in query

    def test_viewport_css_media_query_landscape(self):
        vp = MobileViewport(width=1024, height=768)
        query = vp.css_media_query()
        assert "max-width" in query
        assert "1024px" in query

    def test_viewport_repr(self):
        vp = MobileViewport(width=375, height=667)
        assert "375" in repr(vp)
        assert "667" in repr(vp)

    def test_viewport_from_dict_minimal(self):
        data = {"width": 320}
        vp = MobileViewport.from_dict(data)
        assert vp.width == 320
        assert vp.height == 480  # default

    def test_viewport_physical_dimensions(self):
        vp = MobileViewport(width=375, height=667, device_pixel_ratio=3.0)
        assert vp.physical_width == 1125
        assert vp.physical_height == 2001

    def test_viewport_css_dimensions(self):
        vp = MobileViewport(width=375, height=667, device_pixel_ratio=3.0)
        assert vp.css_width == 375
        assert vp.css_height == 667


class TestMobileBreakpoint:
    """Tests for MobileBreakpoint enum."""

    def test_breakpoint_values(self):
        assert MobileBreakpoint.SMALL.value == "small"
        assert MobileBreakpoint.MEDIUM.value == "medium"
        assert MobileBreakpoint.LARGE.value == "large"
        assert MobileBreakpoint.XLARGE.value == "xlarge"

    def test_breakpoint_max_width(self):
        assert MobileBreakpoint.SMALL.max_width == 640
        assert MobileBreakpoint.MEDIUM.max_width == 768
        assert MobileBreakpoint.LARGE.max_width == 1024
        assert MobileBreakpoint.XLARGE.max_width == 1920

    def test_breakpoint_min_width(self):
        assert MobileBreakpoint.SMALL.min_width == 0
        assert MobileBreakpoint.MEDIUM.min_width == 641
        assert MobileBreakpoint.LARGE.min_width == 769
        assert MobileBreakpoint.XLARGE.min_width == 1025

    def test_breakpoint_matches(self):
        assert MobileBreakpoint.SMALL.matches(375) is True
        assert MobileBreakpoint.SMALL.matches(640) is True
        assert MobileBreakpoint.SMALL.matches(641) is False

    def test_breakpoint_matches_medium(self):
        assert MobileBreakpoint.MEDIUM.matches(700) is True
        assert MobileBreakpoint.MEDIUM.matches(768) is True
        assert MobileBreakpoint.MEDIUM.matches(640) is False

    def test_breakpoint_matches_large(self):
        assert MobileBreakpoint.LARGE.matches(900) is True
        assert MobileBreakpoint.LARGE.matches(1024) is True
        assert MobileBreakpoint.LARGE.matches(768) is False

    def test_breakpoint_matches_xlarge(self):
        assert MobileBreakpoint.XLARGE.matches(1400) is True
        assert MobileBreakpoint.XLARGE.matches(1920) is True
        assert MobileBreakpoint.XLARGE.matches(1024) is False

    def test_breakpoint_from_width(self):
        assert MobileBreakpoint.from_width(375) == MobileBreakpoint.SMALL
        assert MobileBreakpoint.from_width(700) == MobileBreakpoint.MEDIUM
        assert MobileBreakpoint.from_width(900) == MobileBreakpoint.LARGE
        assert MobileBreakpoint.from_width(1400) == MobileBreakpoint.XLARGE

    def test_breakpoint_from_width_edge(self):
        assert MobileBreakpoint.from_width(640) == MobileBreakpoint.SMALL
        assert MobileBreakpoint.from_width(641) == MobileBreakpoint.MEDIUM
        assert MobileBreakpoint.from_width(768) == MobileBreakpoint.MEDIUM
        assert MobileBreakpoint.from_width(769) == MobileBreakpoint.LARGE

    def test_breakpoint_css_query(self):
        query = MobileBreakpoint.SMALL.css_query()
        assert "max-width: 640px" in query

    def test_breakpoint_css_query_medium(self):
        query = MobileBreakpoint.MEDIUM.css_query()
        assert "min-width: 641px" in query
        assert "max-width: 768px" in query


class TestMobileLayout:
    """Tests for MobileLayout enum."""

    def test_layout_values(self):
        assert MobileLayout.LIST.value == "list"
        assert MobileLayout.GRID.value == "grid"
        assert MobileLayout.CARD.value == "card"
        assert MobileLayout.COMPACT.value == "compact"
        assert MobileLayout.FULLSCREEN.value == "fullscreen"

    def test_layout_columns(self):
        assert MobileLayout.LIST.columns == 1
        assert MobileLayout.GRID.columns == 2
        assert MobileLayout.CARD.columns == 1
        assert MobileLayout.COMPACT.columns == 3
        assert MobileLayout.FULLSCREEN.columns == 1

    def test_layout_is_single_column(self):
        assert MobileLayout.LIST.is_single_column() is True
        assert MobileLayout.GRID.is_single_column() is False
        assert MobileLayout.CARD.is_single_column() is True

    def test_layout_default_for_breakpoint(self):
        assert MobileLayout.default_for(MobileBreakpoint.SMALL) == MobileLayout.LIST
        assert MobileLayout.default_for(MobileBreakpoint.MEDIUM) == MobileLayout.GRID
        assert MobileLayout.default_for(MobileBreakpoint.LARGE) == MobileLayout.GRID
        assert MobileLayout.default_for(MobileBreakpoint.XLARGE) == MobileLayout.GRID


class TestMobileTheme:
    """Tests for MobileTheme enum."""

    def test_theme_values(self):
        assert MobileTheme.LIGHT.value == "light"
        assert MobileTheme.DARK.value == "dark"
        assert MobileTheme.SYSTEM.value == "system"

    def test_theme_css_variable(self):
        assert "--theme" in MobileTheme.LIGHT.css_variable()
        assert "light" in MobileTheme.LIGHT.css_variable()

    def test_theme_is_dark(self):
        assert MobileTheme.DARK.is_dark() is True
        assert MobileTheme.LIGHT.is_dark() is False
        assert MobileTheme.SYSTEM.is_dark() is False

    def test_theme_contrast_ratio(self):
        ratio = MobileTheme.DARK.contrast_ratio()
        assert ratio > 0

    def test_theme_css_class(self):
        assert MobileTheme.LIGHT.css_class() == "theme-light"
        assert MobileTheme.DARK.css_class() == "theme-dark"
        assert MobileTheme.SYSTEM.css_class() == "theme-system"


class TestMobilePreferences:
    """Tests for MobilePreferences dataclass."""

    def test_create_preferences_default(self):
        prefs = MobilePreferences()
        assert prefs.theme == MobileTheme.SYSTEM
        assert prefs.layout == MobileLayout.LIST
        assert prefs.font_size == 16
        assert prefs.reduced_motion is False
        assert prefs.high_contrast is False

    def test_create_preferences_custom(self):
        prefs = MobilePreferences(
            theme=MobileTheme.DARK,
            layout=MobileLayout.GRID,
            font_size=18,
            reduced_motion=True,
            high_contrast=True,
        )
        assert prefs.theme == MobileTheme.DARK
        assert prefs.layout == MobileLayout.GRID
        assert prefs.font_size == 18
        assert prefs.reduced_motion is True
        assert prefs.high_contrast is True

    def test_preferences_to_dict(self):
        prefs = MobilePreferences(theme=MobileTheme.DARK, font_size=18)
        d = prefs.to_dict()
        assert d["theme"] == "dark"
        assert d["font_size"] == 18
        assert d["layout"] == "list"

    def test_preferences_from_dict(self):
        data = {"theme": "dark", "layout": "grid", "font_size": 18}
        prefs = MobilePreferences.from_dict(data)
        assert prefs.theme == MobileTheme.DARK
        assert prefs.layout == MobileLayout.GRID
        assert prefs.font_size == 18

    def test_preferences_from_dict_minimal(self):
        data = {}
        prefs = MobilePreferences.from_dict(data)
        assert prefs.theme == MobileTheme.SYSTEM
        assert prefs.font_size == 16

    def test_preferences_css_custom_properties(self):
        prefs = MobilePreferences(theme=MobileTheme.DARK, font_size=18)
        css = prefs.css_custom_properties()
        assert "--font-size" in css
        assert "18px" in css

    def test_preferences_css_custom_properties_dark(self):
        prefs = MobilePreferences(theme=MobileTheme.DARK)
        css = prefs.css_custom_properties()
        assert "--theme" in css

    def test_preferences_css_custom_properties_reduced_motion(self):
        prefs = MobilePreferences(reduced_motion=True)
        css = prefs.css_custom_properties()
        assert "prefers-reduced-motion" in css

    def test_preferences_css_custom_properties_high_contrast(self):
        prefs = MobilePreferences(high_contrast=True)
        css = prefs.css_custom_properties()
        assert "high-contrast" in css

    def test_preferences_update(self):
        prefs = MobilePreferences()
        prefs.update(theme=MobileTheme.DARK)
        assert prefs.theme == MobileTheme.DARK
        assert prefs.font_size == 16  # unchanged

    def test_preferences_update_multiple(self):
        prefs = MobilePreferences()
        prefs.update(theme=MobileTheme.DARK, font_size=20, layout=MobileLayout.GRID)
        assert prefs.theme == MobileTheme.DARK
        assert prefs.font_size == 20
        assert prefs.layout == MobileLayout.GRID

    def test_preferences_merge(self):
        prefs1 = MobilePreferences(theme=MobileTheme.DARK)
        prefs2 = MobilePreferences(font_size=20)
        merged = prefs1.merge(prefs2)
        assert merged.theme == MobileTheme.DARK
        assert merged.font_size == 20

    def test_preferences_repr(self):
        prefs = MobilePreferences(theme=MobileTheme.DARK)
        assert "dark" in repr(prefs)


class TestMobileViewConfig:
    """Tests for MobileViewConfig dataclass."""

    def test_create_view_config_default(self):
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        assert config.viewport.width == 375
        assert config.layout == MobileLayout.LIST
        assert config.theme == MobileTheme.SYSTEM

    def test_create_view_config_custom(self):
        config = MobileViewConfig(
            viewport=MobileViewport(768, 1024),
            layout=MobileLayout.GRID,
            theme=MobileTheme.DARK,
        )
        assert config.layout == MobileLayout.GRID
        assert config.theme == MobileTheme.DARK

    def test_view_config_to_dict(self):
        config = MobileViewConfig(
            viewport=MobileViewport(375, 667),
            layout=MobileLayout.GRID,
            theme=MobileTheme.DARK,
        )
        d = config.to_dict()
        assert d["layout"] == "grid"
        assert d["theme"] == "dark"
        assert "viewport" in d

    def test_view_config_from_dict(self):
        data = {
            "viewport": {"width": 375, "height": 667},
            "layout": "grid",
            "theme": "dark",
            "font_size": 18,
        }
        config = MobileViewConfig.from_dict(data)
        assert config.layout == MobileLayout.GRID
        assert config.theme == MobileTheme.DARK
        assert config.font_size == 18

    def test_view_config_generate_css(self):
        config = MobileViewConfig(
            viewport=MobileViewport(375, 667),
            layout=MobileLayout.LIST,
            theme=MobileTheme.DARK,
        )
        css = config.generate_css()
        assert "body" in css
        assert "--font-size" in css

    def test_view_config_generate_css_grid(self):
        config = MobileViewConfig(
            viewport=MobileViewport(768, 1024),
            layout=MobileLayout.GRID,
        )
        css = config.generate_css()
        assert "grid" in css

    def test_view_config_generate_html_head(self):
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        head = config.generate_html_head()
        assert "viewport" in head
        assert "width=device-width" in head

    def test_view_config_generate_html_head_dark(self):
        config = MobileViewConfig(
            viewport=MobileViewport(375, 667),
            theme=MobileTheme.DARK,
        )
        head = config.generate_html_head()
        assert "dark" in head

    def test_view_config_is_mobile_optimized(self):
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        assert config.is_mobile_optimized() is True

    def test_view_config_is_mobile_optimized_desktop(self):
        config = MobileViewConfig(viewport=MobileViewport(1920, 1080))
        assert config.is_mobile_optimized() is False

    def test_view_config_get_breakpoint(self):
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        assert config.get_breakpoint() == MobileBreakpoint.SMALL

    def test_view_config_get_default_layout(self):
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        assert config.get_default_layout() == MobileLayout.LIST


class TestMobileOptimizationLevel:
    """Tests for MobileOptimizationLevel enum."""

    def test_level_values(self):
        assert MobileOptimizationLevel.NONE.value == "none"
        assert MobileOptimizationLevel.BASIC.value == "basic"
        assert MobileOptimizationLevel.ADVANCED.value == "advanced"
        assert MobileOptimizationLevel.FULL.value == "full"

    def test_level_priority(self):
        assert MobileOptimizationLevel.NONE.priority == 0
        assert MobileOptimizationLevel.BASIC.priority == 1
        assert MobileOptimizationLevel.ADVANCED.priority == 2
        assert MobileOptimizationLevel.FULL.priority == 3

    def test_level_comparison(self):
        assert MobileOptimizationLevel.FULL > MobileOptimizationLevel.BASIC
        assert MobileOptimizationLevel.BASIC > MobileOptimizationLevel.NONE

    def test_level_from_string(self):
        assert MobileOptimizationLevel.from_string("basic") == MobileOptimizationLevel.BASIC
        assert MobileOptimizationLevel.from_string("full") == MobileOptimizationLevel.FULL
        assert MobileOptimizationLevel.from_string("unknown") == MobileOptimizationLevel.NONE


class TestMobileOptimizationResult:
    """Tests for MobileOptimizationResult dataclass."""

    def test_create_result(self):
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=5000,
            level=MobileOptimizationLevel.ADVANCED,
        )
        assert result.original_size == 10000
        assert result.optimized_size == 5000
        assert result.reduction_percent == 50.0

    def test_create_result_no_reduction(self):
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=10000,
            level=MobileOptimizationLevel.NONE,
        )
        assert result.reduction_percent == 0.0

    def test_create_result_to_dict(self):
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=5000,
            level=MobileOptimizationLevel.ADVANCED,
            optimizations_applied=["image_resize", "css_minify"],
        )
        d = result.to_dict()
        assert d["reduction_percent"] == 50.0
        assert d["optimizations_applied"] == ["image_resize", "css_minify"]

    def test_create_result_from_dict(self):
        data = {
            "original_size": 10000,
            "optimized_size": 5000,
            "level": "advanced",
            "optimizations_applied": ["image_resize"],
        }
        result = MobileOptimizationResult.from_dict(data)
        assert result.level == MobileOptimizationLevel.ADVANCED
        assert result.optimizations_applied == ["image_resize"]

    def test_result_add_optimization(self):
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=5000,
            level=MobileOptimizationLevel.BASIC,
        )
        result.add_optimization("css_minify")
        assert "css_minify" in result.optimizations_applied

    def test_result_repr(self):
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=5000,
            level=MobileOptimizationLevel.ADVANCED,
        )
        assert "50.0" in repr(result)


class TestMobileStore:
    """Tests for MobileStore class."""

    def test_create_store(self):
        store = MobileStore()
        assert store.get_preferences("user1") is None

    def test_set_preferences(self):
        store = MobileStore()
        prefs = MobilePreferences(theme=MobileTheme.DARK)
        store.set_preferences("user1", prefs)
        retrieved = store.get_preferences("user1")
        assert retrieved is not None
        assert retrieved.theme == MobileTheme.DARK

    def test_set_preferences_overwrite(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences(theme=MobileTheme.LIGHT))
        store.set_preferences("user1", MobilePreferences(theme=MobileTheme.DARK))
        prefs = store.get_preferences("user1")
        assert prefs.theme == MobileTheme.DARK

    def test_get_preferences_default(self):
        store = MobileStore()
        prefs = store.get_preferences("user1", default=MobilePreferences(theme=MobileTheme.DARK))
        assert prefs.theme == MobileTheme.DARK

    def test_set_view_config(self):
        store = MobileStore()
        config = MobileViewConfig(viewport=MobileViewport(375, 667))
        store.set_view_config("user1", config)
        retrieved = store.get_view_config("user1")
        assert retrieved is not None
        assert retrieved.viewport.width == 375

    def test_get_view_config_default(self):
        store = MobileStore()
        config = store.get_view_config("user1")
        assert config is None

    def test_list_users(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences())
        store.set_preferences("user2", MobilePreferences())
        users = store.list_users()
        assert "user1" in users
        assert "user2" in users

    def test_delete_user(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences())
        store.delete_user("user1")
        assert store.get_preferences("user1") is None

    def test_get_optimization_result(self):
        store = MobileStore()
        result = MobileOptimizationResult(
            original_size=10000,
            optimized_size=5000,
            level=MobileOptimizationLevel.ADVANCED,
        )
        store.set_optimization_result("page1", result)
        retrieved = store.get_optimization_result("page1")
        assert retrieved is not None
        assert retrieved.reduction_percent == 50.0

    def test_list_optimization_results(self):
        store = MobileStore()
        store.set_optimization_result("page1", MobileOptimizationResult(1000, 500, MobileOptimizationLevel.BASIC))
        store.set_optimization_result("page2", MobileOptimizationResult(2000, 1000, MobileOptimizationLevel.ADVANCED))
        results = store.list_optimization_results()
        assert len(results) == 2

    def test_clear_optimization_results(self):
        store = MobileStore()
        store.set_optimization_result("page1", MobileOptimizationResult(1000, 500, MobileOptimizationLevel.BASIC))
        store.clear_optimization_results()
        assert store.get_optimization_result("page1") is None

    def test_store_stats(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences())
        store.set_preferences("user2", MobilePreferences())
        stats = store.get_stats()
        assert stats["total_users"] == 2

    def test_store_serialize(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences(theme=MobileTheme.DARK))
        data = store.serialize()
        assert "user1" in data

    def test_store_deserialize(self):
        store = MobileStore()
        data = {"user1": {"theme": "dark", "layout": "list", "font_size": 16}}
        store.deserialize(data)
        prefs = store.get_preferences("user1")
        assert prefs is not None
        assert prefs.theme == MobileTheme.DARK

    def test_store_clear(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences())
        store.clear()
        assert store.get_preferences("user1") is None
        assert len(store.list_users()) == 0

    def test_store_get_or_create_preferences(self):
        store = MobileStore()
        prefs = store.get_or_create_preferences("user1")
        assert prefs is not None
        assert prefs.theme == MobileTheme.SYSTEM

    def test_store_get_or_create_preferences_existing(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences(theme=MobileTheme.DARK))
        prefs = store.get_or_create_preferences("user1")
        assert prefs.theme == MobileTheme.DARK

    def test_store_update_preferences(self):
        store = MobileStore()
        store.set_preferences("user1", MobilePreferences(theme=MobileTheme.LIGHT))
        store.update_preferences("user1", theme=MobileTheme.DARK)
        prefs = store.get_preferences("user1")
        assert prefs.theme == MobileTheme.DARK

    def test_store_update_preferences_not_found(self):
        store = MobileStore()
        store.update_preferences("user1", theme=MobileTheme.DARK)
        assert store.get_preferences("user1") is None

    def test_store_detect_device(self):
        store = MobileStore()
        device = store.detect_device("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)")
        assert device["is_mobile"] is True

    def test_store_detect_device_android(self):
        store = MobileStore()
        device = store.detect_device("Mozilla/5.0 (Linux; Android 13)")
        assert device["is_mobile"] is True

    def test_store_detect_device_desktop(self):
        store = MobileStore()
        device = store.detect_device("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        assert device["is_mobile"] is False

    def test_store_detect_device_tablet(self):
        store = MobileStore()
        device = store.detect_device("Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)")
        assert device["is_tablet"] is True

    def test_store_generate_meta_tags(self):
        store = MobileStore()
        tags = store.generate_meta_tags("My App", "A personal index")
        assert "viewport" in tags
        assert "My App" in tags

    def test_store_generate_meta_tags_with_theme(self):
        store = MobileStore()
        tags = store.generate_meta_tags("My App", "Desc", theme_color="#1a1a1a")
        assert "theme-color" in tags
        assert "#1a1a1a" in tags

    def test_store_generate_og_tags(self):
        store = MobileStore()
        tags = store.generate_og_tags("Title", "https://example.com", "Description")
        assert "og:title" in tags
        assert "og:url" in tags
        assert "og:description" in tags

    def test_store_generate_twitter_tags(self):
        store = MobileStore()
        tags = store.generate_twitter_tags("Title", "https://example.com/image.png")
        assert "twitter:title" in tags
        assert "twitter:image" in tags
