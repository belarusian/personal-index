"""Tests for content_thumbnail module - generate thumbnails for saved items."""

import pytest
from personal_index.content_thumbnail import (
    ThumbnailConfig,
    ThumbnailEngine,
    ThumbnailFormat,
    ThumbnailGenerator,
    ThumbnailMetadata,
    ThumbnailProcessor,
    ThumbnailResult,
    ThumbnailSize,
    ThumbnailStatus,
    ThumbnailStyle,
)


class TestThumbnailSize:
    def test_small_dimensions(self):
        size = ThumbnailSize.SMALL
        assert size.width == 64
        assert size.height == 64

    def test_medium_dimensions(self):
        size = ThumbnailSize.MEDIUM
        assert size.width == 128
        assert size.height == 128

    def test_large_dimensions(self):
        size = ThumbnailSize.LARGE
        assert size.width == 256
        assert size.height == 256

    def test_xlarge_dimensions(self):
        size = ThumbnailSize.XLARGE
        assert size.width == 512
        assert size.height == 512

    def test_custom_size(self):
        size = ThumbnailSize(width=100, height=200)
        assert size.width == 100
        assert size.height == 200

    def test_size_area(self):
        size = ThumbnailSize(width=100, height=200)
        assert size.area() == 20000

    def test_size_equals(self):
        assert ThumbnailSize(width=64, height=64) == ThumbnailSize(width=64, height=64)
        assert ThumbnailSize(width=64, height=64) != ThumbnailSize(width=128, height=128)


class TestThumbnailFormat:
    def test_png_value(self):
        assert ThumbnailFormat.PNG.value == "png"

    def test_jpeg_value(self):
        assert ThumbnailFormat.JPEG.value == "jpeg"

    def test_webp_value(self):
        assert ThumbnailFormat.WEBP.value == "webp"

    def test_svg_value(self):
        assert ThumbnailFormat.SVG.value == "svg"

    def test_format_mime_type(self):
        assert ThumbnailFormat.PNG.mime_type() == "image/png"
        assert ThumbnailFormat.JPEG.mime_type() == "image/jpeg"
        assert ThumbnailFormat.WEBP.mime_type() == "image/webp"
        assert ThumbnailFormat.SVG.mime_type() == "image/svg+xml"

    def test_format_extension(self):
        assert ThumbnailFormat.PNG.extension() == ".png"
        assert ThumbnailFormat.JPEG.extension() == ".jpeg"
        assert ThumbnailFormat.WEBP.extension() == ".webp"
        assert ThumbnailFormat.SVG.extension() == ".svg"


class TestThumbnailStyle:
    def test_simple_style(self):
        style = ThumbnailStyle.SIMPLE
        assert style.value == "simple"

    def test_gradient_style(self):
        style = ThumbnailStyle.GRADIENT
        assert style.value == "gradient"

    def test_card_style(self):
        style = ThumbnailStyle.CARD
        assert style.value == "card"

    def test_minimal_style(self):
        style = ThumbnailStyle.MINIMAL
        assert style.value == "minimal"


class TestThumbnailStatus:
    def test_pending_status(self):
        assert ThumbnailStatus.PENDING.value == "pending"

    def test_generating_status(self):
        assert ThumbnailStatus.GENERATING.value == "generating"

    def test_ready_status(self):
        assert ThumbnailStatus.READY.value == "ready"

    def test_failed_status(self):
        assert ThumbnailStatus.FAILED.value == "failed"

    def test_cached_status(self):
        assert ThumbnailStatus.CACHED.value == "cached"


class TestThumbnailConfig:
    def test_default_config(self):
        config = ThumbnailConfig()
        assert config.size == ThumbnailSize.MEDIUM
        assert config.format == ThumbnailFormat.PNG
        assert config.style == ThumbnailStyle.SIMPLE
        assert config.background_color == "#ffffff"
        assert config.text_color == "#333333"
        assert config.border_radius == 0
        assert config.include_domain == True
        assert config.include_title == True
        assert config.max_title_length == 50
        assert config.cache_ttl_seconds == 86400

    def test_custom_config(self):
        config = ThumbnailConfig(
            size=ThumbnailSize.LARGE,
            format=ThumbnailFormat.WEBP,
            style=ThumbnailStyle.GRADIENT,
            background_color="#000000",
            text_color="#ffffff",
            border_radius=8,
            include_domain=False,
            include_title=False,
            max_title_length=100,
            cache_ttl_seconds=3600,
        )
        assert config.size == ThumbnailSize.LARGE
        assert config.format == ThumbnailFormat.WEBP
        assert config.style == ThumbnailStyle.GRADIENT
        assert config.background_color == "#000000"
        assert config.text_color == "#ffffff"
        assert config.border_radius == 8
        assert config.include_domain is False
        assert config.include_title is False
        assert config.max_title_length == 100
        assert config.cache_ttl_seconds == 3600

    def test_config_to_dict(self):
        config = ThumbnailConfig(
            size=ThumbnailSize.SMALL,
            format=ThumbnailFormat.JPEG,
        )
        d = config.to_dict()
        assert d["size"]["width"] == 64
        assert d["format"] == "jpeg"

    def test_config_from_dict(self):
        data = {
            "size": {"width": 256, "height": 256},
            "format": "webp",
            "style": "gradient",
            "background_color": "#123456",
            "text_color": "#ffffff",
            "border_radius": 4,
            "include_domain": True,
            "include_title": True,
            "max_title_length": 75,
            "cache_ttl_seconds": 7200,
        }
        config = ThumbnailConfig.from_dict(data)
        assert config.size.width == 256
        assert config.format == ThumbnailFormat.WEBP
        assert config.style == ThumbnailStyle.GRADIENT
        assert config.background_color == "#123456"
        assert config.border_radius == 4
        assert config.max_title_length == 75
        assert config.cache_ttl_seconds == 7200

    def test_config_from_dict_defaults(self):
        config = ThumbnailConfig.from_dict({})
        assert config.size == ThumbnailSize.MEDIUM
        assert config.format == ThumbnailFormat.PNG

    def test_config_with_custom_size(self):
        config = ThumbnailConfig(size=ThumbnailSize(width=300, height=200))
        assert config.size.width == 300
        assert config.size.height == 200
