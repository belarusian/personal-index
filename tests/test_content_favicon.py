"""Tests for content_favicon module - extract favicons from saved URLs."""

import pytest
from personal_index.content_favicon import (
    FaviconConfig,
    FaviconExtractor,
    FaviconFormat,
    FaviconInfo,
    FaviconManager,
    FaviconResult,
    FaviconSource,
    FaviconStatus,
    FaviconStore,
)


class TestFaviconFormat:
    def test_ico_value(self):
        assert FaviconFormat.ICO.value == "ico"

    def test_png_value(self):
        assert FaviconFormat.PNG.value == "png"

    def test_svg_value(self):
        assert FaviconFormat.SVG.value == "svg"

    def test_any_value(self):
        assert FaviconFormat.ANY.value == "any"

    def test_format_extension(self):
        assert FaviconFormat.ICO.extension() == ".ico"
        assert FaviconFormat.PNG.extension() == ".png"
        assert FaviconFormat.SVG.extension() == ".svg"

    def test_format_mime_type(self):
        assert FaviconFormat.ICO.mime_type() == "image/x-icon"
        assert FaviconFormat.PNG.mime_type() == "image/png"
        assert FaviconFormat.SVG.mime_type() == "image/svg+xml"


class TestFaviconSource:
    def test_head_tag(self):
        assert FaviconSource.HEAD_TAG.value == "head_tag"

    def test_default_path(self):
        assert FaviconSource.DEFAULT_PATH.value == "default_path"

    def test_google_service(self):
        assert FaviconSource.GOOGLE_SERVICE.value == "google_service"

    def test_dns_txt(self):
        assert FaviconSource.DNS_TXT.value == "dns_txt"


class TestFaviconStatus:
    def test_pending(self):
        assert FaviconStatus.PENDING.value == "pending"

    def test_extracting(self):
        assert FaviconStatus.EXTRACTING.value == "extracting"

    def test_ready(self):
        assert FaviconStatus.READY.value == "ready"

    def test_failed(self):
        assert FaviconStatus.FAILED.value == "failed"

    def test_cached(self):
        assert FaviconStatus.CACHED.value == "cached"


class TestFaviconConfig:
    def test_default_config(self):
        config = FaviconConfig()
        assert config.preferred_format == FaviconFormat.ANY
        assert config.size == 32
        assert config.cache_ttl_seconds == 86400
        assert config.timeout_seconds == 10
        assert config.fallback_to_google == True
        assert config.max_size_bytes == 102400

    def test_custom_config(self):
        config = FaviconConfig(
            preferred_format=FaviconFormat.PNG,
            size=64,
            cache_ttl_seconds=3600,
            timeout_seconds=5,
            fallback_to_google=False,
            max_size_bytes=51200,
        )
        assert config.preferred_format == FaviconFormat.PNG
        assert config.size == 64
        assert config.cache_ttl_seconds == 3600
        assert config.timeout_seconds == 5
        assert config.fallback_to_google is False
        assert config.max_size_bytes == 51200

    def test_config_to_dict(self):
        config = FaviconConfig(size=16, preferred_format=FaviconFormat.SVG)
        d = config.to_dict()
        assert d["size"] == 16
        assert d["preferred_format"] == "svg"

    def test_config_from_dict(self):
        data = {
            "preferred_format": "png",
            "size": 48,
            "cache_ttl_seconds": 7200,
            "timeout_seconds": 15,
            "fallback_to_google": True,
            "max_size_bytes": 204800,
        }
        config = FaviconConfig.from_dict(data)
        assert config.preferred_format == FaviconFormat.PNG
        assert config.size == 48
        assert config.cache_ttl_seconds == 7200
        assert config.timeout_seconds == 15
        assert config.fallback_to_google is True
        assert config.max_size_bytes == 204800

    def test_config_from_dict_defaults(self):
        config = FaviconConfig.from_dict({})
        assert config.preferred_format == FaviconFormat.ANY
        assert config.size == 32


class TestFaviconInfo:
    def test_create_info(self):
        info = FaviconInfo(
            url="https://example.com/favicon.ico",
            format=FaviconFormat.ICO,
            size=32,
            source=FaviconSource.HEAD_TAG,
        )
        assert info.url == "https://example.com/favicon.ico"
        assert info.format == FaviconFormat.ICO
        assert info.size == 32
        assert info.source == FaviconSource.HEAD_TAG

    def test_info_to_dict(self):
        info = FaviconInfo(
            url="https://example.com/favicon.png",
            format=FaviconFormat.PNG,
            size=64,
            source=FaviconSource.DEFAULT_PATH,
        )
        d = info.to_dict()
        assert d["url"] == "https://example.com/favicon.png"
        assert d["format"] == "png"
        assert d["size"] == 64

    def test_info_from_dict(self):
        data = {
            "url": "https://example.com/favicon.svg",
            "format": "svg",
            "size": 128,
            "source": "google_service",
            "width": 128,
            "height": 128,
        }
        info = FaviconInfo.from_dict(data)
        assert info.url == "https://example.com/favicon.svg"
        assert info.format == FaviconFormat.SVG
        assert info.size == 128
        assert info.source == FaviconSource.GOOGLE_SERVICE

    def test_info_with_dimensions(self):
        info = FaviconInfo(
            url="https://example.com/favicon.png",
            format=FaviconFormat.PNG,
            size=32,
            width=32,
            height=32,
        )
        assert info.width == 32
        assert info.height == 32


class TestFaviconResult:
    def test_ready_result(self):
        result = FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
            format=FaviconFormat.ICO,
            size=32,
            source=FaviconSource.HEAD_TAG,
        )
        assert result.is_ready() is True
        assert result.is_failed() is False

    def test_failed_result(self):
        result = FaviconResult(
            domain="example.com",
            url="",
            status=FaviconStatus.FAILED,
            error="Not found",
        )
        assert result.is_ready() is False
        assert result.is_failed() is True
        assert result.error == "Not found"

    def test_pending_result(self):
        result = FaviconResult(
            domain="example.com",
            url="",
            status=FaviconStatus.PENDING,
        )
        assert result.is_ready() is False
        assert result.is_failed() is False

    def test_result_to_dict(self):
        result = FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
            format=FaviconFormat.ICO,
            size=32,
        )
        d = result.to_dict()
        assert d["domain"] == "example.com"
        assert d["status"] == "ready"
        assert d["format"] == "ico"

    def test_result_from_dict(self):
        data = {
            "domain": "example.com",
            "url": "https://example.com/favicon.png",
            "status": "ready",
            "format": "png",
            "size": 64,
            "source": "default_path",
        }
        result = FaviconResult.from_dict(data)
        assert result.domain == "example.com"
        assert result.status == FaviconStatus.READY
        assert result.format == FaviconFormat.PNG
        assert result.source == FaviconSource.DEFAULT_PATH


class TestFaviconExtractor:
    def test_extract_from_url_default(self):
        extractor = FaviconExtractor()
        url = extractor.get_favicon_url("https://example.com/page")
        assert url == "https://example.com/favicon.ico"

    def test_extract_from_url_with_path(self):
        extractor = FaviconExtractor()
        url = extractor.get_favicon_url("https://example.com/some/path")
        assert url == "https://example.com/favicon.ico"

    def test_extract_from_url_http(self):
        extractor = FaviconExtractor()
        url = extractor.get_favicon_url("http://example.com/page")
        assert url == "http://example.com/favicon.ico"

    def test_extract_from_url_preserve_scheme(self):
        extractor = FaviconExtractor()
        url = extractor.get_favicon_url("https://sub.example.com/page")
        assert url == "https://sub.example.com/favicon.ico"

    def test_extract_from_html_head_tag(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="icon" href="/custom-icon.png" type="image/png"/></head>'
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert "custom-icon.png" in result.url

    def test_extract_from_html_apple_touch_icon(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="apple-touch-icon" href="/apple-icon.png"/></head>'
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert "apple-icon.png" in result.url

    def test_extract_from_html_shortcut_icon(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="shortcut icon" href="/shortcut.ico" type="image/x-icon"/></head>'
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert "shortcut.ico" in result.url

    def test_extract_from_html_no_favicon(self):
        extractor = FaviconExtractor()
        html = "<html><head><title>No Favicon</title></head></html>"
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert "favicon.ico" in result.url

    def test_extract_from_html_relative_url(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="icon" href="images/icon.png"/></head>'
        result = extractor.extract_from_html(html, "https://example.com/page")
        assert result is not None
        assert "images/icon.png" in result.url

    def test_extract_from_html_absolute_url(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="icon" href="https://cdn.example.com/icon.png"/></head>'
        result = extractor.extract_from_html(html, "https://example.com/page")
        assert result is not None
        assert "cdn.example.com" in result.url

    def test_extract_format_from_type(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="icon" href="/icon.svg" type="image/svg+xml"/></head>'
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert result.format == FaviconFormat.SVG

    def test_extract_format_from_extension(self):
        extractor = FaviconExtractor()
        html = '<head><link rel="icon" href="/icon.png"/></head>'
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert result.format == FaviconFormat.PNG

    def test_extract_multiple_favicons_prefers_icon(self):
        extractor = FaviconExtractor()
        html = """
        <head>
            <link rel="apple-touch-icon" href="/apple.png"/>
            <link rel="icon" href="/main.ico" type="image/x-icon"/>
        </head>
        """
        result = extractor.extract_from_html(html, "https://example.com")
        assert result is not None
        assert "main.ico" in result.url

    def test_get_google_favicon_url(self):
        extractor = FaviconExtractor()
        url = extractor.get_google_favicon_url("example.com")
        assert "google.com/s2/favicons" in url
        assert "example.com" in url

    def test_get_google_favicon_url_with_size(self):
        extractor = FaviconExtractor()
        url = extractor.get_google_favicon_url("example.com", size=64)
        assert "s=64" in url

    def test_extract_domain_from_url(self):
        extractor = FaviconExtractor()
        domain = extractor.extract_domain("https://www.example.com/page")
        assert domain == "www.example.com"

    def test_extract_domain_from_url_no_www(self):
        extractor = FaviconExtractor()
        domain = extractor.extract_domain("https://example.com/page")
        assert domain == "example.com"


class TestFaviconStore:
    def test_store_and_retrieve(self):
        store = FaviconStore()
        result = FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
            format=FaviconFormat.ICO,
        )
        store.store("example.com", result)
        retrieved = store.get("example.com")
        assert retrieved is not None
        assert retrieved.url == "https://example.com/favicon.ico"

    def test_store_not_found(self):
        store = FaviconStore()
        retrieved = store.get("nonexistent.com")
        assert retrieved is None

    def test_store_overwrite(self):
        store = FaviconStore()
        store.store("example.com", FaviconResult(
            domain="example.com",
            url="https://example.com/old.ico",
            status=FaviconStatus.READY,
        ))
        store.store("example.com", FaviconResult(
            domain="example.com",
            url="https://example.com/new.ico",
            status=FaviconStatus.READY,
        ))
        retrieved = store.get("example.com")
        assert retrieved.url == "https://example.com/new.ico"

    def test_store_contains(self):
        store = FaviconStore()
        store.store("example.com", FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
        ))
        assert store.contains("example.com") is True
        assert store.contains("other.com") is False

    def test_store_count(self):
        store = FaviconStore()
        assert store.count() == 0
        store.store("a.com", FaviconResult(domain="a.com", url="https://a.com/f.ico", status=FaviconStatus.READY))
        store.store("b.com", FaviconResult(domain="b.com", url="https://b.com/f.ico", status=FaviconStatus.READY))
        assert store.count() == 2

    def test_store_remove(self):
        store = FaviconStore()
        store.store("example.com", FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
        ))
        store.remove("example.com")
        assert store.get("example.com") is None

    def test_store_clear(self):
        store = FaviconStore()
        store.store("a.com", FaviconResult(domain="a.com", url="https://a.com/f.ico", status=FaviconStatus.READY))
        store.store("b.com", FaviconResult(domain="b.com", url="https://b.com/f.ico", status=FaviconStatus.READY))
        store.clear()
        assert store.count() == 0

    def test_store_all_domains(self):
        store = FaviconStore()
        store.store("a.com", FaviconResult(domain="a.com", url="https://a.com/f.ico", status=FaviconStatus.READY))
        store.store("b.com", FaviconResult(domain="b.com", url="https://b.com/f.ico", status=FaviconStatus.READY))
        domains = store.all_domains()
        assert set(domains) == {"a.com", "b.com"}

    def test_store_to_dict(self):
        store = FaviconStore()
        store.store("example.com", FaviconResult(
            domain="example.com",
            url="https://example.com/favicon.ico",
            status=FaviconStatus.READY,
        ))
        d = store.to_dict()
        assert "example.com" in d

    def test_store_from_dict(self):
        data = {
            "example.com": {
                "domain": "example.com",
                "url": "https://example.com/favicon.ico",
                "status": "ready",
                "format": "ico",
                "size": 32,
            }
        }
        store = FaviconStore.from_dict(data)
        result = store.get("example.com")
        assert result is not None
        assert result.url == "https://example.com/favicon.ico"


class TestFaviconManager:
    def test_extract_favicon(self):
        mgr = FaviconManager()
        result = mgr.extract_favicon("https://example.com/page")
        assert result.domain == "example.com"
        assert result.url == "https://example.com/favicon.ico"

    def test_extract_favicon_with_html(self):
        mgr = FaviconManager()
        html = '<head><link rel="icon" href="/custom.png" type="image/png"/></head>'
        result = mgr.extract_favicon("https://example.com/page", html=html)
        assert result.domain == "example.com"
        assert "custom.png" in result.url

    def test_extract_favicon_with_fallback(self):
        mgr = FaviconManager(fallback_to_google=True)
        result = mgr.extract_favicon("https://example.com/page", fallback_google=True)
        assert result.domain == "example.com"

    def test_batch_extract(self):
        mgr = FaviconManager()
        urls = [
            "https://example.com/a",
            "https://test.com/b",
            "https://other.com/c",
        ]
        results = mgr.batch_extract(urls)
        assert len(results) == 3
        assert results[0].domain == "example.com"
        assert results[1].domain == "test.com"

    def test_get_cached_favicon(self):
        mgr = FaviconManager()
        mgr.extract_favicon("https://example.com/page")
        cached = mgr.get_cached("example.com")
        assert cached is not None

    def test_get_cached_not_found(self):
        mgr = FaviconManager()
        cached = mgr.get_cached("nonexistent.com")
        assert cached is None

    def test_refresh_favicon(self):
        mgr = FaviconManager()
        mgr.extract_favicon("https://example.com/page")
        result = mgr.refresh_favicon("example.com")
        assert result.domain == "example.com"

    def test_get_summary(self):
        mgr = FaviconManager()
        mgr.extract_favicon("https://example.com/a")
        mgr.extract_favicon("https://test.com/b")
        summary = mgr.get_summary()
        assert summary["total"] == 2
        assert summary["ready"] == 2

    def test_clear_cache(self):
        mgr = FaviconManager()
        mgr.extract_favicon("https://example.com/a")
        cleared = mgr.clear_cache()
        assert cleared == 1
        assert mgr.get_cached("example.com") is None
