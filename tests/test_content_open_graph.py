"""Tests for content_open_graph module - extract Open Graph metadata."""

import pytest
from personal_index.content_open_graph import (
    OpenGraphConfig,
    OpenGraphExtractor,
    OpenGraphImage,
    OpenGraphManager,
    OpenGraphMetadata,
    OpenGraphParser,
    OpenGraphResult,
    OpenGraphStatus,
    OpenGraphStore,
    OpenGraphType,
)


class TestOpenGraphType:
    def test_article(self):
        assert OpenGraphType.ARTICLE.value == "article"

    def test_website(self):
        assert OpenGraphType.WEBSITE.value == "website"

    def test_video(self):
        assert OpenGraphType.VIDEO.value == "video"

    def test_music(self):
        assert OpenGraphType.MUSIC.value == "music"

    def test_profile(self):
        assert OpenGraphType.PROFILE.value == "profile"

    def test_book(self):
        assert OpenGraphType.BOOK.value == "book"


class TestOpenGraphStatus:
    def test_pending(self):
        assert OpenGraphStatus.PENDING.value == "pending"

    def test_extracting(self):
        assert OpenGraphStatus.EXTRACTING.value == "extracting"

    def test_ready(self):
        assert OpenGraphStatus.READY.value == "ready"

    def test_failed(self):
        assert OpenGraphStatus.FAILED.value == "failed"

    def test_cached(self):
        assert OpenGraphStatus.CACHED.value == "cached"


class TestOpenGraphImage:
    def test_create_image(self):
        img = OpenGraphImage(url="https://example.com/img.jpg", width=1200, height=630)
        assert img.url == "https://example.com/img.jpg"
        assert img.width == 1200
        assert img.height == 630
        assert img.type == "jpg"

    def test_image_type_from_url(self):
        img = OpenGraphImage(url="https://example.com/img.png")
        assert img.type == "png"

    def test_image_type_svg(self):
        img = OpenGraphImage(url="https://example.com/img.svg")
        assert img.type == "svg"

    def test_image_type_unknown(self):
        img = OpenGraphImage(url="https://example.com/img")
        assert img.type == ""

    def test_image_is_valid(self):
        img = OpenGraphImage(url="https://example.com/img.jpg", width=1200, height=630)
        assert img.is_valid() is True

    def test_image_is_valid_no_url(self):
        img = OpenGraphImage(url="", width=1200, height=630)
        assert img.is_valid() is False

    def test_image_to_dict(self):
        img = OpenGraphImage(url="https://example.com/img.jpg", width=1200, height=630)
        d = img.to_dict()
        assert d["url"] == "https://example.com/img.jpg"
        assert d["width"] == 1200

    def test_image_from_dict(self):
        data = {"url": "https://example.com/img.png", "width": 800, "height": 600, "type": "png"}
        img = OpenGraphImage.from_dict(data)
        assert img.url == "https://example.com/img.png"
        assert img.width == 800
        assert img.type == "png"


class TestOpenGraphConfig:
    def test_default_config(self):
        config = OpenGraphConfig()
        assert config.cache_ttl_seconds == 86400
        assert config.timeout_seconds == 10
        assert config.max_images == 5
        assert config.include_twitter_cards == True
        assert config.include_microdata == False

    def test_custom_config(self):
        config = OpenGraphConfig(
            cache_ttl_seconds=3600,
            timeout_seconds=5,
            max_images=10,
            include_twitter_cards=False,
            include_microdata=True,
        )
        assert config.cache_ttl_seconds == 3600
        assert config.timeout_seconds == 5
        assert config.max_images == 10
        assert config.include_twitter_cards is False
        assert config.include_microdata is True

    def test_config_to_dict(self):
        config = OpenGraphConfig(max_images=3)
        d = config.to_dict()
        assert d["max_images"] == 3

    def test_config_from_dict(self):
        data = {"max_images": 7, "include_twitter_cards": False}
        config = OpenGraphConfig.from_dict(data)
        assert config.max_images == 7
        assert config.include_twitter_cards is False

    def test_config_from_dict_defaults(self):
        config = OpenGraphConfig.from_dict({})
        assert config.cache_ttl_seconds == 86400
        assert config.include_twitter_cards is True


class TestOpenGraphMetadata:
    def test_create_metadata(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="Test Page",
            description="A test page",
            type=OpenGraphType.ARTICLE,
            site_name="Example",
        )
        assert meta.url == "https://example.com/page"
        assert meta.title == "Test Page"
        assert meta.description == "A test page"
        assert meta.type == OpenGraphType.ARTICLE
        assert meta.site_name == "Example"

    def test_metadata_with_images(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="Test",
            images=[OpenGraphImage(url="https://example.com/img.jpg", width=1200, height=630)],
        )
        assert len(meta.images) == 1
        assert meta.images[0].url == "https://example.com/img.jpg"

    def test_metadata_with_locale(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="Test",
            locale="en_US",
        )
        assert meta.locale == "en_US"

    def test_metadata_to_dict(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            type=OpenGraphType.WEBSITE,
        )
        d = meta.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["title"] == "Test"
        assert d["type"] == "website"

    def test_metadata_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "title": "Test",
            "description": "Desc",
            "type": "article",
            "site_name": "Example",
            "locale": "en_US",
            "images": [{"url": "https://example.com/img.jpg", "width": 1200, "height": 630}],
        }
        meta = OpenGraphMetadata.from_dict(data)
        assert meta.url == "https://example.com/page"
        assert meta.type == OpenGraphType.ARTICLE
        assert meta.locale == "en_US"
        assert len(meta.images) == 1

    def test_metadata_has_complete_info(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="Test",
            description="Desc",
            images=[OpenGraphImage(url="https://example.com/img.jpg", width=1200, height=630)],
        )
        assert meta.has_complete_info() is True

    def test_metadata_has_complete_info_missing(self):
        meta = OpenGraphMetadata(
            url="https://example.com/page",
            title="",
            description="",
        )
        assert meta.has_complete_info() is False


class TestOpenGraphResult:
    def test_ready_result(self):
        result = OpenGraphResult(
            url="https://example.com/page",
            status=OpenGraphStatus.READY,
            metadata=OpenGraphMetadata(url="https://example.com/page", title="Test"),
        )
        assert result.is_ready() is True
        assert result.is_failed() is False

    def test_failed_result(self):
        result = OpenGraphResult(
            url="https://example.com/page",
            status=OpenGraphStatus.FAILED,
            error="Timeout",
        )
        assert result.is_ready() is False
        assert result.is_failed() is True
        assert result.error == "Timeout"

    def test_result_to_dict(self):
        result = OpenGraphResult(
            url="https://example.com/page",
            status=OpenGraphStatus.READY,
            metadata=OpenGraphMetadata(url="https://example.com/page", title="Test"),
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["status"] == "ready"

    def test_result_from_dict(self):
        data = {
            "url": "https://example.com/page",
            "status": "ready",
            "metadata": {
                "url": "https://example.com/page",
                "title": "Test",
                "description": "Desc",
                "type": "website",
            },
        }
        result = OpenGraphResult.from_dict(data)
        assert result.url == "https://example.com/page"
        assert result.status == OpenGraphStatus.READY
        assert result.metadata.title == "Test"


class TestOpenGraphParser:
    def test_parse_og_title(self):
        parser = OpenGraphParser()
        html = '<meta property="og:title" content="Test Title"/>'
        result = parser.parse(html, "https://example.com")
        assert result.title == "Test Title"

    def test_parse_og_description(self):
        parser = OpenGraphParser()
        html = '<meta property="og:description" content="Test Description"/>'
        result = parser.parse(html, "https://example.com")
        assert result.description == "Test Description"

    def test_parse_og_image(self):
        parser = OpenGraphParser()
        html = '<meta property="og:image" content="https://example.com/img.jpg"/>'
        result = parser.parse(html, "https://example.com")
        assert len(result.images) == 1
        assert result.images[0].url == "https://example.com/img.jpg"

    def test_parse_og_image_with_dimensions(self):
        parser = OpenGraphParser()
        html = """
        <meta property="og:image" content="https://example.com/img.jpg"/>
        <meta property="og:image:width" content="1200"/>
        <meta property="og:image:height" content="630"/>
        """
        result = parser.parse(html, "https://example.com")
        assert len(result.images) == 1
        assert result.images[0].width == 1200
        assert result.images[0].height == 630

    def test_parse_og_type(self):
        parser = OpenGraphParser()
        html = '<meta property="og:type" content="article"/>'
        result = parser.parse(html, "https://example.com")
        assert result.type == OpenGraphType.ARTICLE

    def test_parse_og_type_unknown(self):
        parser = OpenGraphParser()
        html = '<meta property="og:type" content="custom_type"/>'
        result = parser.parse(html, "https://example.com")
        assert result.type == OpenGraphType.WEBSITE

    def test_parse_og_url(self):
        parser = OpenGraphParser()
        html = '<meta property="og:url" content="https://example.com/canonical"/>'
        result = parser.parse(html, "https://example.com/page")
        assert result.url == "https://example.com/canonical"

    def test_parse_og_site_name(self):
        parser = OpenGraphParser()
        html = '<meta property="og:site_name" content="Example Site"/>'
        result = parser.parse(html, "https://example.com")
        assert result.site_name == "Example Site"

    def test_parse_og_locale(self):
        parser = OpenGraphParser()
        html = '<meta property="og:locale" content="en_US"/>'
        result = parser.parse(html, "https://example.com")
        assert result.locale == "en_US"

    def test_parse_twitter_card(self):
        parser = OpenGraphParser()
        html = '<meta name="twitter:card" content="summary_large_image"/>'
        result = parser.parse(html, "https://example.com")
        assert result.twitter_card == "summary_large_image"

    def test_parse_twitter_image(self):
        parser = OpenGraphParser()
        html = '<meta name="twitter:image" content="https://example.com/twitter.jpg"/>'
        result = parser.parse(html, "https://example.com")
        assert len(result.twitter_images) == 1

    def test_parse_no_og_tags(self):
        parser = OpenGraphParser()
        html = "<html><head><title>No OG</title></head></html>"
        result = parser.parse(html, "https://example.com")
        assert result.title == ""
        assert result.description == ""

    def test_parse_multiple_images(self):
        parser = OpenGraphParser()
        html = """
        <meta property="og:image" content="https://example.com/img1.jpg"/>
        <meta property="og:image" content="https://example.com/img2.jpg"/>
        """
        result = parser.parse(html, "https://example.com")
        assert len(result.images) == 2

    def test_parse_og_video(self):
        parser = OpenGraphParser()
        html = '<meta property="og:video" content="https://example.com/video.mp4"/>'
        result = parser.parse(html, "https://example.com")
        assert result.video_url == "https://example.com/video.mp4"

    def test_parse_og_audio(self):
        parser = OpenGraphParser()
        html = '<meta property="og:audio" content="https://example.com/audio.mp3"/>'
        result = parser.parse(html, "https://example.com")
        assert result.audio_url == "https://example.com/audio.mp3"

    def test_parse_og_determiner(self):
        parser = OpenGraphParser()
        html = '<meta property="og:determiner" content="the"/>'
        result = parser.parse(html, "https://example.com")
        assert result.determiner == "the"


class TestOpenGraphExtractor:
    def test_extract_from_html(self):
        extractor = OpenGraphExtractor()
        html = """
        <html>
        <head>
            <meta property="og:title" content="Test Title"/>
            <meta property="og:description" content="Test Description"/>
            <meta property="og:image" content="https://example.com/img.jpg"/>
            <meta property="og:type" content="article"/>
        </head>
        </html>
        """
        result = extractor.extract(html, "https://example.com/page")
        assert result.title == "Test Title"
        assert result.description == "Test Description"
        assert len(result.images) == 1

    def test_extract_empty_html(self):
        extractor = OpenGraphExtractor()
        result = extractor.extract("", "https://example.com/page")
        assert result.title == ""
        assert result.url == "https://example.com/page"

    def test_extract_with_config(self):
        config = OpenGraphConfig(max_images=2)
        extractor = OpenGraphExtractor(config=config)
        html = """
        <meta property="og:image" content="https://example.com/img1.jpg"/>
        <meta property="og:image" content="https://example.com/img2.jpg"/>
        <meta property="og:image" content="https://example.com/img3.jpg"/>
        """
        result = extractor.extract(html, "https://example.com/page")
        assert len(result.images) <= 2


class TestOpenGraphStore:
    def test_store_and_retrieve(self):
        store = OpenGraphStore()
        meta = OpenGraphMetadata(url="https://example.com/page", title="Test")
        store.store("https://example.com/page", meta)
        retrieved = store.get("https://example.com/page")
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_store_not_found(self):
        store = OpenGraphStore()
        retrieved = store.get("https://nonexistent.com/page")
        assert retrieved is None

    def test_store_overwrite(self):
        store = OpenGraphStore()
        store.store("https://example.com/page", OpenGraphMetadata(url="https://example.com/page", title="Old"))
        store.store("https://example.com/page", OpenGraphMetadata(url="https://example.com/page", title="New"))
        retrieved = store.get("https://example.com/page")
        assert retrieved.title == "New"

    def test_store_count(self):
        store = OpenGraphStore()
        store.store("https://a.com", OpenGraphMetadata(url="https://a.com", title="A"))
        store.store("https://b.com", OpenGraphMetadata(url="https://b.com", title="B"))
        assert store.count() == 2

    def test_store_clear(self):
        store = OpenGraphStore()
        store.store("https://a.com", OpenGraphMetadata(url="https://a.com", title="A"))
        store.clear()
        assert store.count() == 0

    def test_store_to_dict(self):
        store = OpenGraphStore()
        store.store("https://example.com/page", OpenGraphMetadata(url="https://example.com/page", title="Test"))
        d = store.to_dict()
        assert "https://example.com/page" in d

    def test_store_from_dict(self):
        data = {
            "https://example.com/page": {
                "url": "https://example.com/page",
                "title": "Test",
                "description": "Desc",
                "type": "website",
            }
        }
        store = OpenGraphStore.from_dict(data)
        meta = store.get("https://example.com/page")
        assert meta is not None
        assert meta.title == "Test"


class TestOpenGraphManager:
    def test_extract_and_store(self):
        mgr = OpenGraphManager()
        html = '<meta property="og:title" content="Test"/>'
        result = mgr.extract(html, "https://example.com/page")
        assert result.title == "Test"
        cached = mgr.get_cached("https://example.com/page")
        assert cached is not None

    def test_batch_extract(self):
        mgr = OpenGraphManager()
        items = [
            {"url": "https://a.com", "html": '<meta property="og:title" content="A"/>'},
            {"url": "https://b.com", "html": '<meta property="og:title" content="B"/>'},
        ]
        results = mgr.batch_extract(items)
        assert len(results) == 2
        assert results[0].title == "A"
        assert results[1].title == "B"

    def test_get_summary(self):
        mgr = OpenGraphManager()
        mgr.extract('<meta property="og:title" content="A"/>', "https://a.com")
        mgr.extract('<meta property="og:title" content="B"/>', "https://b.com")
        summary = mgr.get_summary()
        assert summary["total"] == 2

    def test_clear_cache(self):
        mgr = OpenGraphManager()
        mgr.extract('<meta property="og:title" content="A"/>', "https://a.com")
        cleared = mgr.clear_cache()
        assert cleared == 1
