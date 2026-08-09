"""Tests for content_social_preview module - generate social media preview cards."""

import pytest
from personal_index.content_social_preview import (
    PreviewCardConfig,
    PreviewCardGenerator,
    PreviewCardManager,
    PreviewCardResult,
    PreviewCardSize,
    PreviewCardStyle,
    PreviewCardTemplate,
    PreviewCardType,
    SocialPlatform,
    SocialPreviewConfig,
    SocialPreviewEngine,
    SocialPreviewResult,
    SocialPreviewStatus,
)


class TestSocialPlatform:
    def test_twitter(self):
        assert SocialPlatform.TWITTER.value == "twitter"
        assert SocialPlatform.TWITTER.max_title_length == 70
        assert SocialPlatform.TWITTER.max_description_length == 200

    def test_facebook(self):
        assert SocialPlatform.FACEBOOK.value == "facebook"
        assert SocialPlatform.FACEBOOK.max_title_length == 60
        assert SocialPlatform.FACEBOOK.max_description_length == 110

    def test_linkedin(self):
        assert SocialPlatform.LINKEDIN.value == "linkedin"
        assert SocialPlatform.LINKEDIN.max_title_length == 200
        assert SocialPlatform.LINKEDIN.max_description_length == 300

    def test_slack(self):
        assert SocialPlatform.SLACK.value == "slack"
        assert SocialPlatform.SLACK.max_title_length == 80
        assert SocialPlatform.SLACK.max_description_length == 250

    def test_discord(self):
        assert SocialPlatform.DISCORD.value == "discord"
        assert SocialPlatform.DISCORD.max_title_length == 80
        assert SocialPlatform.DISCORD.max_description_length == 250

    def test_telegram(self):
        assert SocialPlatform.TELEGRAM.value == "telegram"

    def test_whatsapp(self):
        assert SocialPlatform.WHATSAPP.value == "whatsapp"

    def test_generic(self):
        assert SocialPlatform.GENERIC.value == "generic"


class TestPreviewCardType:
    def test_summary(self):
        assert PreviewCardType.SUMMARY.value == "summary"

    def test_summary_large_image(self):
        assert PreviewCardType.SUMMARY_LARGE_IMAGE.value == "summary_large_image"

    def test_app(self):
        assert PreviewCardType.APP.value == "app"

    def test_player(self):
        assert PreviewCardType.PLAYER.value == "player"


class TestPreviewCardSize:
    def test_twitter_small(self):
        size = PreviewCardSize.TWITTER_SMALL
        assert size.width == 280
        assert size.height == 150

    def test_twitter_large(self):
        size = PreviewCardSize.TWITTER_LARGE
        assert size.width == 1200
        assert size.height == 628

    def test_facebook(self):
        size = PreviewCardSize.FACEBOOK
        assert size.width == 1200
        assert size.height == 630

    def test_linkedin(self):
        size = PreviewCardSize.LINKEDIN
        assert size.width == 1200
        assert size.height == 627

    def test_square(self):
        size = PreviewCardSize.SQUARE
        assert size.width == 1200
        assert size.height == 1200

    def test_custom(self):
        size = PreviewCardSize(width=800, height=600)
        assert size.width == 800
        assert size.height == 600

    def test_size_aspect_ratio(self):
        size = PreviewCardSize(width=1200, height=630)
        assert abs(size.aspect_ratio() - 1.905) < 0.01

    def test_size_equals(self):
        assert PreviewCardSize(width=1200, height=630) == PreviewCardSize(width=1200, height=630)


class TestPreviewCardStyle:
    def test_modern(self):
        assert PreviewCardStyle.MODERN.value == "modern"

    def test_classic(self):
        assert PreviewCardStyle.CLASSIC.value == "classic"

    def test_minimal(self):
        assert PreviewCardStyle.MINIMAL.value == "minimal"

    def test_bold(self):
        assert PreviewCardStyle.BOLD.value == "bold"

    def test_dark(self):
        assert PreviewCardStyle.DARK.value == "dark"


class TestSocialPreviewStatus:
    def test_pending(self):
        assert SocialPreviewStatus.PENDING.value == "pending"

    def test_generating(self):
        assert SocialPreviewStatus.GENERATING.value == "generating"

    def test_ready(self):
        assert SocialPreviewStatus.READY.value == "ready"

    def test_failed(self):
        assert SocialPreviewStatus.FAILED.value == "failed"

    def test_cached(self):
        assert SocialPreviewStatus.CACHED.value == "cached"


class TestSocialPreviewConfig:
    def test_default_config(self):
        config = SocialPreviewConfig()
        assert config.platform == SocialPlatform.GENERIC
        assert config.card_type == PreviewCardType.SUMMARY
        assert config.include_domain == True
        assert config.include_favicon == True
        assert config.background_color == "#ffffff"
        assert config.text_color == "#333333"
        assert config.cache_ttl_seconds == 86400

    def test_custom_config(self):
        config = SocialPreviewConfig(
            platform=SocialPlatform.TWITTER,
            card_type=PreviewCardType.SUMMARY_LARGE_IMAGE,
            include_domain=False,
            include_favicon=False,
            background_color="#000000",
            text_color="#ffffff",
            cache_ttl_seconds=3600,
        )
        assert config.platform == SocialPlatform.TWITTER
        assert config.card_type == PreviewCardType.SUMMARY_LARGE_IMAGE
        assert config.include_domain is False
        assert config.background_color == "#000000"

    def test_config_to_dict(self):
        config = SocialPreviewConfig(platform=SocialPlatform.FACEBOOK)
        d = config.to_dict()
        assert d["platform"] == "facebook"

    def test_config_from_dict(self):
        data = {
            "platform": "twitter",
            "card_type": "summary_large_image",
            "background_color": "#123456",
        }
        config = SocialPreviewConfig.from_dict(data)
        assert config.platform == SocialPlatform.TWITTER
        assert config.card_type == PreviewCardType.SUMMARY_LARGE_IMAGE
        assert config.background_color == "#123456"

    def test_config_from_dict_defaults(self):
        config = SocialPreviewConfig.from_dict({})
        assert config.platform == SocialPlatform.GENERIC


class TestPreviewCardConfig:
    def test_default_config(self):
        config = PreviewCardConfig()
        assert config.size == PreviewCardSize.FACEBOOK
        assert config.style == PreviewCardStyle.MODERN
        assert config.background_color == "#ffffff"
        assert config.text_color == "#333333"
        assert config.font_family == "sans-serif"
        assert config.border_radius == 0
        assert config.padding == 20

    def test_custom_config(self):
        config = PreviewCardConfig(
            size=PreviewCardSize.TWITTER_LARGE,
            style=PreviewCardStyle.DARK,
            background_color="#1a1a2e",
            text_color="#eaeaea",
            font_family="Georgia",
            border_radius=8,
            padding=30,
        )
        assert config.size == PreviewCardSize.TWITTER_LARGE
        assert config.style == PreviewCardStyle.DARK
        assert config.background_color == "#1a1a2e"
        assert config.border_radius == 8

    def test_config_to_dict(self):
        config = PreviewCardConfig(style=PreviewCardStyle.BOLD)
        d = config.to_dict()
        assert d["style"] == "bold"

    def test_config_from_dict(self):
        data = {"style": "dark", "background_color": "#000000", "border_radius": 12}
        config = PreviewCardConfig.from_dict(data)
        assert config.style == PreviewCardStyle.DARK
        assert config.background_color == "#000000"
        assert config.border_radius == 12


class TestPreviewCardTemplate:
    def test_get_template_modern(self):
        template = PreviewCardTemplate.get_template(PreviewCardStyle.MODERN)
        assert template is not None

    def test_get_template_classic(self):
        template = PreviewCardTemplate.get_template(PreviewCardStyle.CLASSIC)
        assert template is not None

    def test_get_template_minimal(self):
        template = PreviewCardTemplate.get_template(PreviewCardStyle.MINIMAL)
        assert template is not None

    def test_get_template_bold(self):
        template = PreviewCardTemplate.get_template(PreviewCardStyle.BOLD)
        assert template is not None

    def test_get_template_dark(self):
        template = PreviewCardTemplate.get_template(PreviewCardStyle.DARK)
        assert template is not None

    def test_get_template_default(self):
        template = PreviewCardTemplate.get_template("unknown_style")
        assert template is not None


class TestPreviewCardGenerator:
    def test_generate_card_svg(self):
        config = PreviewCardConfig()
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test Title",
            description="Test Description",
            domain="example.com",
        )
        assert "<svg" in svg
        assert "Test Title" in svg
        assert "Test Description" in svg

    def test_generate_card_with_dimensions(self):
        config = PreviewCardConfig(size=PreviewCardSize.TWITTER_LARGE)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert 'width="1200"' in svg
        assert 'height="628"' in svg

    def test_generate_card_dark_style(self):
        config = PreviewCardConfig(style=PreviewCardStyle.DARK)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "#1a1a2e" in svg or "#121212" in svg

    def test_generate_card_truncate_title(self):
        config = PreviewCardConfig(max_title_length=10)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="This is a very long title that should be truncated",
            domain="example.com",
        )
        assert "very long" not in svg or "..." in svg

    def test_generate_card_with_border_radius(self):
        config = PreviewCardConfig(border_radius=8)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert 'rx="8"' in svg

    def test_generate_card_without_domain(self):
        config = PreviewCardConfig(include_domain=False)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        assert "example.com" not in svg

    def test_generate_card_with_favicon(self):
        config = PreviewCardConfig(include_favicon=True)
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            favicon_url="https://example.com/favicon.ico",
        )
        assert "favicon" in svg or "icon" in svg

    def test_generate_card_with_image(self):
        config = PreviewCardConfig()
        generator = PreviewCardGenerator(config)
        svg = generator.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            image_url="https://example.com/img.jpg",
        )
        assert "img.jpg" in svg or "image" in svg.lower()


class TestPreviewCardResult:
    def test_ready_result(self):
        result = PreviewCardResult(
            url="https://example.com/page",
            status=SocialPreviewStatus.READY,
            svg_content="<svg></svg>",
        )
        assert result.is_ready() is True
        assert result.is_failed() is False

    def test_failed_result(self):
        result = PreviewCardResult(
            url="https://example.com/page",
            status=SocialPreviewStatus.FAILED,
            error="Generation failed",
        )
        assert result.is_ready() is False
        assert result.is_failed() is True

    def test_result_to_dict(self):
        result = PreviewCardResult(
            url="https://example.com/page",
            status=SocialPreviewStatus.READY,
            svg_content="<svg></svg>",
            width=1200,
            height=630,
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["status"] == "ready"
        assert d["width"] == 1200

    def test_result_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "status": "ready",
            "svg_content": "<svg></svg>",
            "width": 1200,
            "height": 630,
        }
        result = PreviewCardResult.from_dict(data)
        assert result.url == "https://example.com/page"
        assert result.status == SocialPreviewStatus.READY
        assert result.width == 1200


class TestSocialPreviewResult:
    def test_ready_result(self):
        result = SocialPreviewResult(
            url="https://example.com/page",
            platform=SocialPlatform.TWITTER,
            status=SocialPreviewStatus.READY,
        )
        assert result.is_ready() is True

    def test_failed_result(self):
        result = SocialPreviewResult(
            url="https://example.com/page",
            platform=SocialPlatform.FACEBOOK,
            status=SocialPreviewStatus.FAILED,
            error="Failed",
        )
        assert result.is_failed() is True

    def test_result_to_dict(self):
        result = SocialPreviewResult(
            url="https://example.com/page",
            platform=SocialPlatform.TWITTER,
            status=SocialPreviewStatus.READY,
            og_title="Test",
            og_description="Desc",
        )
        d = result.to_dict()
        assert d["platform"] == "twitter"
        assert d["og_title"] == "Test"

    def test_result_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "platform": "facebook",
            "status": "ready",
            "og_title": "Test",
        }
        result = SocialPreviewResult.from_dict(data)
        assert result.platform == SocialPlatform.FACEBOOK
        assert result.og_title == "Test"


class TestSocialPreviewEngine:
    def test_generate_preview(self):
        engine = SocialPreviewEngine()
        result = engine.generate_preview(
            url="https://example.com/page",
            title="Test Title",
            description="Test Description",
            image_url="https://example.com/img.jpg",
            platform=SocialPlatform.TWITTER,
        )
        assert result.url == "https://example.com/page"
        assert result.platform == SocialPlatform.TWITTER

    def test_generate_preview_facebook(self):
        engine = SocialPreviewEngine()
        result = engine.generate_preview(
            url="https://example.com/page",
            title="Test",
            platform=SocialPlatform.FACEBOOK,
        )
        assert result.platform == SocialPlatform.FACEBOOK

    def test_generate_card(self):
        engine = SocialPreviewEngine()
        svg = engine.generate_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
            style=PreviewCardStyle.MODERN,
        )
        assert "<svg" in svg

    def test_generate_card_batch(self):
        engine = SocialPreviewEngine()
        items = [
            {"url": "https://a.com", "title": "A", "domain": "a.com"},
            {"url": "https://b.com", "title": "B", "domain": "b.com"},
        ]
        svgs = engine.generate_card_batch(items)
        assert len(svgs) == 2

    def test_get_cached_preview(self):
        engine = SocialPreviewEngine()
        engine.generate_preview(
            url="https://example.com/page",
            title="Test",
            platform=SocialPlatform.TWITTER,
        )
        cached = engine.get_cached("https://example.com/page")
        assert cached is not None

    def test_get_summary(self):
        engine = SocialPreviewEngine()
        engine.generate_preview(
            url="https://a.com", title="A", platform=SocialPlatform.TWITTER,
        )
        engine.generate_preview(
            url="https://b.com", title="B", platform=SocialPlatform.FACEBOOK,
        )
        summary = engine.get_summary()
        assert summary["total"] == 2

    def test_clear_cache(self):
        engine = SocialPreviewEngine()
        engine.generate_preview(
            url="https://example.com/page", title="Test", platform=SocialPlatform.TWITTER,
        )
        cleared = engine.clear_cache()
        assert cleared == 1


class TestPreviewCardManager:
    def test_create_card(self):
        mgr = PreviewCardManager()
        result = mgr.create_card(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            domain="example.com",
        )
        assert result.is_ready() is True

    def test_create_card_batch(self):
        mgr = PreviewCardManager()
        items = [
            {"url": "https://a.com", "title": "A", "domain": "a.com"},
            {"url": "https://b.com", "title": "B", "domain": "b.com"},
        ]
        results = mgr.create_card_batch(items)
        assert len(results) == 2

    def test_get_card(self):
        mgr = PreviewCardManager()
        result = mgr.create_card(
            url="https://example.com/page",
            title="Test",
            domain="example.com",
        )
        card = mgr.get_card("https://example.com/page")
        assert card is not None

    def test_get_summary(self):
        mgr = PreviewCardManager()
        mgr.create_card(url="https://a.com", title="A", domain="a.com")
        mgr.create_card(url="https://b.com", title="B", domain="b.com")
        summary = mgr.get_summary()
        assert summary["total"] == 2
