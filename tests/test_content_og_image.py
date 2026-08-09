"""Tests for content_og_image module - generate Open Graph images."""

import pytest
from personal_index.content_og_image import (
    OGImageBackground,
    OGImageConfig,
    OGImageEngine,
    OGImageGenerator,
    OGImageLayout,
    OGImageManager,
    OGImageMetadata,
    OGImageResult,
    OGImageSize,
    OGImageStatus,
    OGImageStyle,
    OGImageTextConfig,
    OGImageWatermark,
)


class TestOGImageSize:
    def test_facebook(self):
        size = OGImageSize.FACEBOOK
        assert size.width == 1200
        assert size.height == 630

    def test_twitter_large(self):
        size = OGImageSize.TWITTER_LARGE
        assert size.width == 1200
        assert size.height == 628

    def test_twitter_small(self):
        size = OGImageSize.TWITTER_SMALL
        assert size.width == 600
        assert size.height == 314

    def test_square(self):
        size = OGImageSize.SQUARE
        assert size.width == 1200
        assert size.height == 1200

    def test_linkedin(self):
        size = OGImageSize.LINKEDIN
        assert size.width == 1200
        assert size.height == 627

    def test_custom(self):
        size = OGImageSize(width=800, height=600)
        assert size.width == 800
        assert size.height == 600

    def test_size_equals(self):
        assert OGImageSize(width=1200, height=630) == OGImageSize(width=1200, height=630)
        assert OGImageSize(width=1200, height=630) != OGImageSize(width=800, height=600)

    def test_size_area(self):
        size = OGImageSize(width=100, height=200)
        assert size.area() == 20000

    def test_size_aspect_ratio(self):
        size = OGImageSize(width=1200, height=630)
        assert abs(size.aspect_ratio() - 1.905) < 0.01


class TestOGImageStyle:
    def test_gradient(self):
        assert OGImageStyle.GRADIENT.value == "gradient"

    def test_solid(self):
        assert OGImageStyle.SOLID.value == "solid"

    def test_pattern(self):
        assert OGImageStyle.PATTERN.value == "pattern"

    def test_photo(self):
        assert OGImageStyle.PHOTO.value == "photo"

    def test_minimal(self):
        assert OGImageStyle.MINIMAL.value == "minimal"


class TestOGImageLayout:
    def test_center(self):
        assert OGImageLayout.CENTER.value == "center"

    def test_left(self):
        assert OGImageLayout.LEFT.value == "left"

    def test_right(self):
        assert OGImageLayout.RIGHT.value == "right"

    def test_top(self):
        assert OGImageLayout.TOP.value == "top"

    def test_bottom(self):
        assert OGImageLayout.BOTTOM.value == "bottom"


class TestOGImageBackground:
    def test_solid_background(self):
        bg = OGImageBackground(type="solid", color="#ffffff")
        assert bg.type == "solid"
        assert bg.color == "#ffffff"

    def test_gradient_background(self):
        bg = OGImageBackground(type="gradient", colors=["#ff0000", "#0000ff"])
        assert bg.type == "gradient"
        assert bg.colors == ["#ff0000", "#0000ff"]

    def test_background_to_dict(self):
        bg = OGImageBackground(type="solid", color="#000000")
        d = bg.to_dict()
        assert d["type"] == "solid"
        assert d["color"] == "#000000"

    def test_background_from_dict(self):
        data = {"type": "gradient", "colors": ["#ff0000", "#00ff00"]}
        bg = OGImageBackground.from_dict(data)
        assert bg.type == "gradient"
        assert bg.colors == ["#ff0000", "#00ff00"]


class TestOGImageTextConfig:
    def test_default_text_config(self):
        config = OGImageTextConfig()
        assert config.font_family == "sans-serif"
        assert config.title_size == 48
        assert config.description_size == 24
        assert config.domain_size == 18
        assert config.title_color == "#000000"
        assert config.description_color == "#666666"
        assert config.domain_color == "#999999"
        assert config.title_weight == "bold"

    def test_custom_text_config(self):
        config = OGImageTextConfig(
            font_family="Georgia",
            title_size=60,
            description_size=30,
            title_color="#ffffff",
        )
        assert config.font_family == "Georgia"
        assert config.title_size == 60
        assert config.description_size == 30
        assert config.title_color == "#ffffff"

    def test_text_config_to_dict(self):
        config = OGImageTextConfig(title_size=56)
        d = config.to_dict()
        assert d["title_size"] == 56

    def test_text_config_from_dict(self):
        data = {"font_family": "Arial", "title_size": 72, "title_color": "#ffffff"}
        config = OGImageTextConfig.from_dict(data)
        assert config.font_family == "Arial"
        assert config.title_size == 72
        assert config.title_color == "#ffffff"


class TestOGImageWatermark:
    def test_create_watermark(self):
        wm = OGImageWatermark(text="© Example", position="bottom-right", opacity=0.5)
        assert wm.text == "© Example"
        assert wm.position == "bottom-right"
        assert wm.opacity == 0.5

    def test_watermark_to_dict(self):
        wm = OGImageWatermark(text="© Test", position="bottom-left", opacity=0.3)
        d = wm.to_dict()
        assert d["text"] == "© Test"
        assert d["position"] == "bottom-left"

    def test_watermark_from_dict(self):
        data = {"text": "© Test", "position": "top-right", "opacity": 0.7, "font_size": 14}
        wm = OGImageWatermark.from_dict(data)
        assert wm.text == "© Test"
        assert wm.position == "top-right"
        assert wm.opacity == 0.7
        assert wm.font_size == 14


class TestOGImageStatus:
    def test_pending(self):
        assert OGImageStatus.PENDING.value == "pending"

    def test_generating(self):
        assert OGImageStatus.GENERATING.value == "generating"

    def test_ready(self):
        assert OGImageStatus.READY.value == "ready"

    def test_failed(self):
        assert OGImageStatus.FAILED.value == "failed"

    def test_cached(self):
        assert OGImageStatus.CACHED.value == "cached"


class TestOGImageConfig:
    def test_default_config(self):
        config = OGImageConfig()
        assert config.size == OGImageSize.FACEBOOK
        assert config.style == OGImageStyle.GRADIENT
        assert config.layout == OGImageLayout.CENTER
        assert config.background.type == "gradient"
        assert config.cache_ttl_seconds == 86400
        assert config.max_title_length == 60
        assert config.max_description_length == 150

    def test_custom_config(self):
        config = OGImageConfig(
            size=OGImageSize.TWITTER_LARGE,
            style=OGImageStyle.SOLID,
            layout=OGImageLayout.LEFT,
            max_title_length=80,
        )
        assert config.size == OGImageSize.TWITTER_LARGE
        assert config.style == OGImageStyle.SOLID
        assert config.layout == OGImageLayout.LEFT
        assert config.max_title_length == 80

    def test_config_to_dict(self):
        config = OGImageConfig(style=OGImageStyle.MINIMAL)
        d = config.to_dict()
        assert d["style"] == "minimal"

    def test_config_from_dict(self):
        data = {
            "style": "solid",
            "layout": "left",
            "max_title_length": 100,
            "background": {"type": "solid", "color": "#000000"},
        }
        config = OGImageConfig.from_dict(data)
        assert config.style == OGImageStyle.SOLID
        assert config.layout == OGImageLayout.LEFT
        assert config.max_title_length == 100
        assert config.background.type == "solid"

    def test_config_from_dict_defaults(self):
        config = OGImageConfig.from_dict({})
        assert config.size == OGImageSize.FACEBOOK
        assert config.style == OGImageStyle.GRADIENT


class TestOGImageMetadata:
    def test_create_metadata(self):
        meta = OGImageMetadata(
            url="https://example.com/page",
            title="Test Title",
            description="Test Description",
            domain="example.com",
        )
        assert meta.url == "https://example.com/page"
        assert meta.title == "Test Title"
        assert meta.domain == "example.com"

    def test_metadata_with_favicon(self):
        meta = OGImageMetadata(
            url="https://example.com/page",
            title="Test",
            favicon_url="https://example.com/favicon.ico",
        )
        assert meta.favicon_url == "https://example.com/favicon.ico"

    def test_metadata_with_tags(self):
        meta = OGImageMetadata(
            url="https://example.com/page",
            title="Test",
            tags=["python", "web"],
        )
        assert meta.tags == ["python", "web"]

    def test_metadata_to_dict(self):
        meta = OGImageMetadata(
            url="https://example.com/page",
            title="Test",
            description="Desc",
        )
        d = meta.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["title"] == "Test"

    def test_metadata_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "title": "Test",
            "description": "Desc",
            "domain": "example.com",
            "tags": ["python"],
        }
        meta = OGImageMetadata.from_dict(data)
        assert meta.url == "https://example.com/page"
        assert meta.title == "Test"
        assert meta.tags == ["python"]


class TestOGImageResult:
    def test_ready_result(self):
        result = OGImageResult(
            url="https://example.com/page",
            status=OGImageStatus.READY,
            svg_content="<svg></svg>",
        )
        assert result.is_ready() is True
        assert result.is_failed() is False

    def test_failed_result(self):
        result = OGImageResult(
            url="https://example.com/page",
            status=OGImageStatus.FAILED,
            error="Generation failed",
        )
        assert result.is_ready() is False
        assert result.is_failed() is True

    def test_result_to_dict(self):
        result = OGImageResult(
            url="https://example.com/page",
            status=OGImageStatus.READY,
            svg_content="<svg></svg>",
            width=1200,
            height=630,
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["width"] == 1200

    def test_result_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "status": "ready",
            "svg_content": "<svg></svg>",
            "width": 1200,
            "height": 630,
        }
        result = OGImageResult.from_dict(data)
        assert result.url == "https://example.com/page"
        assert result.status == OGImageStatus.READY
        assert result.width == 1200


class TestOGImageGenerator:
    def test_generate_basic(self):
        generator = OGImageGenerator()
        svg = generator.generate(
            url="https://example.com/page",
            title="Test Title",
            description="Test Description",
            domain="example.com",
        )
        assert "<svg" in svg
        assert "Test Title" in svg
        assert "Test Description" in svg

    def test_generate_with_config(self):
        config = OGImageConfig(style=OGImageStyle.SOLID)
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "<svg" in svg

    def test_generate_with_size(self):
        config = OGImageConfig(size=OGImageSize.TWITTER_LARGE)
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert 'width="1200"' in svg
        assert 'height="628"' in svg

    def test_generate_with_layout(self):
        config = OGImageConfig(layout=OGImageLayout.LEFT)
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "<svg" in svg

    def test_generate_with_watermark(self):
        config = OGImageConfig(
            watermark=OGImageWatermark(text="© Example", position="bottom-right")
        )
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "© Example" in svg

    def test_generate_truncate_title(self):
        config = OGImageConfig(max_title_length=10)
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="This is a very long title that should be truncated",
            domain="example.com",
        )
        assert "very long" not in svg or "..." in svg

    def test_generate_with_tags(self):
        generator = OGImageGenerator()
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            tags=["python", "web"],
        )
        assert "python" in svg

    def test_generate_with_favicon(self):
        generator = OGImageGenerator()
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            favicon_url="https://example.com/favicon.ico",
        )
        assert "favicon" in svg or "icon" in svg

    def test_generate_gradient_style(self):
        config = OGImageConfig(style=OGImageStyle.GRADIENT)
        generator = OGImageGenerator(config=config)
        svg = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "gradient" in svg.lower() or "Gradient" in svg

    def test_generate_cached(self):
        generator = OGImageGenerator()
        svg1 = generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        cached = generator.get_cached("https://example.com/page")
        assert cached is not None

    def test_generate_clear_cache(self):
        generator = OGImageGenerator()
        generator.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        cleared = generator.clear_cache()
        assert cleared == 1


class TestOGImageManager:
    def test_create_image(self):
        mgr = OGImageManager()
        result = mgr.create_image(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            domain="example.com",
        )
        assert result.is_ready() is True

    def test_create_image_batch(self):
        mgr = OGImageManager()
        items = [
            {"url": "https://a.com", "title": "A", "domain": "a.com"},
            {"url": "https://b.com", "title": "B", "domain": "b.com"},
        ]
        results = mgr.create_image_batch(items)
        assert len(results) == 2

    def test_get_image(self):
        mgr = OGImageManager()
        mgr.create_image(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        result = mgr.get_image("https://example.com/page")
        assert result is not None

    def test_get_summary(self):
        mgr = OGImageManager()
        mgr.create_image(url="https://a.com", title="A", domain="a.com")
        mgr.create_image(url="https://b.com", title="B", domain="b.com")
        summary = mgr.get_summary()
        assert summary["total"] == 2

    def test_clear_cache(self):
        mgr = OGImageManager()
        mgr.create_image(url="https://a.com", title="A", domain="a.com")
        cleared = mgr.clear_cache()
        assert cleared == 1


class TestOGImageEngine:
    def test_generate(self):
        engine = OGImageEngine()
        result = engine.generate(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            domain="example.com",
        )
        assert result.is_ready() is True

    def test_generate_with_style(self):
        engine = OGImageEngine()
        result = engine.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            style=OGImageStyle.SOLID,
        )
        assert result.is_ready() is True

    def test_generate_batch(self):
        engine = OGImageEngine()
        items = [
            {"url": "https://a.com", "title": "A", "domain": "a.com"},
            {"url": "https://b.com", "title": "B", "domain": "b.com"},
        ]
        results = engine.generate_batch(items)
        assert len(results) == 2

    def test_get_svg(self):
        engine = OGImageEngine()
        svg = engine.get_svg(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "<svg" in svg

    def test_get_cached(self):
        engine = OGImageEngine()
        engine.generate(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        cached = engine.get_cached("https://example.com/page")
        assert cached is not None

    def test_get_summary(self):
        engine = OGImageEngine()
        engine.generate(url="https://a.com", title="A", domain="a.com")
        summary = engine.get_summary()
        assert summary["total"] == 1

    def test_clear_cache(self):
        engine = OGImageEngine()
        engine.generate(url="https://a.com", title="A", domain="a.com")
        cleared = engine.clear_cache()
        assert cleared == 1
