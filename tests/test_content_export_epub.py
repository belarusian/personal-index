"""Tests for content export as EPUB ebooks."""

import io
import os
import zipfile
import pytest
from datetime import datetime, timezone
from personal_index.content_export_epub import (
    EPUBExporter,
    EPUBExportConfig,
    EPUBExportResult,
    EPUBContentItem,
    EPUBChapterFormat,
)


class TestEPUBExportConfig:
    def test_default_config(self):
        config = EPUBExportConfig()
        assert config.title == "Content Export"
        assert config.author == "personal-index"
        assert config.language == "en"
        assert config.include_cover is True
        assert config.include_toc is True
        assert config.chapter_format == EPUBChapterFormat.HTML

    def test_custom_config(self):
        config = EPUBExportConfig(
            title="My Book",
            author="Jane Doe",
            language="fr",
            include_cover=False,
            include_toc=False,
            chapter_format=EPUBChapterFormat.TEXT,
        )
        assert config.title == "My Book"
        assert config.author == "Jane Doe"
        assert config.language == "fr"
        assert config.include_cover is False
        assert config.include_toc is False
        assert config.chapter_format == EPUBChapterFormat.TEXT

    def test_to_dict(self):
        config = EPUBExportConfig(title="Test", author="Author")
        d = config.to_dict()
        assert d["title"] == "Test"
        assert d["author"] == "Author"
        assert d["language"] == "en"
        assert d["include_cover"] is True
        assert d["include_toc"] is True


class TestEPUBChapterFormat:
    def test_html_format(self):
        assert EPUBChapterFormat.HTML.value == "html"

    def test_text_format(self):
        assert EPUBChapterFormat.TEXT.value == "text"


class TestEPUBContentItem:
    def test_create_item(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Example Page",
            content="Some content here",
        )
        assert item.url == "http://example.com"
        assert item.title == "Example Page"
        assert item.content == "Some content here"
        assert item.word_count == 0
        assert item.tags == []

    def test_create_item_with_all_fields(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Full Item",
            content="Hello world this is content",
            word_count=5,
            category="tech",
            tags=["python", "web"],
            created_at="2024-01-01T00:00:00Z",
        )
        assert item.word_count == 5
        assert item.category == "tech"
        assert item.tags == ["python", "web"]
        assert item.created_at == "2024-01-01T00:00:00Z"

    def test_to_dict(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Test",
            content="Body",
            word_count=10,
            tags=["tag1"],
        )
        d = item.to_dict()
        assert d["url"] == "http://example.com"
        assert d["title"] == "Test"
        assert d["word_count"] == 10
        assert d["tags"] == ["tag1"]

    def test_format_as_html(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="HTML Test",
            content="Some <b>content</b>",
            tags=["test"],
            created_at="2024-01-01",
        )
        html = item.format_as_html()
        assert "<html " in html or "<html>" in html
        assert "<title>HTML Test</title>" in html
        assert "test" in html

    def test_format_as_text(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Text Test",
            content="Plain content",
        )
        text = item.format_as_text()
        assert "Text Test" in text
        assert "Plain content" in text
        assert "http://example.com" in text

    def test_format_as_html_escapes_content(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Escape Test",
            content="<script>alert('xss')</script>",
        )
        html = item.format_as_html()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_format_as_html_escapes_title(self):
        item = EPUBContentItem(
            url="http://example.com",
            title="Title with <special> chars",
            content="Body",
        )
        html = item.format_as_html()
        assert "<special>" not in html
        assert "&lt;special&gt;" in html


class TestEPUBExportResult:
    def test_default_result(self):
        result = EPUBExportResult()
        assert result.success is True
        assert result.items_exported == 0
        assert result.errors == []
        assert result.output is None

    def test_result_with_data(self):
        result = EPUBExportResult(
            success=True,
            items_exported=5,
            output=b"fake epub bytes",
        )
        assert result.success is True
        assert result.items_exported == 5
        assert result.output == b"fake epub bytes"

    def test_result_with_errors(self):
        result = EPUBExportResult(
            success=False,
            errors=["something went wrong"],
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_to_dict(self):
        result = EPUBExportResult(items_exported=10)
        d = result.to_dict()
        assert d["items_exported"] == 10
        assert d["success"] is True


class TestEPUBExporterEmpty:
    def test_export_empty_items(self):
        exporter = EPUBExporter()
        result = exporter.export([])
        assert result.success is True
        assert result.items_exported == 0
        assert result.output is not None

    def test_export_empty_items_produces_valid_zip(self):
        exporter = EPUBExporter()
        result = exporter.export([])
        assert result.output is not None
        # Should be a valid zip file
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            assert "mimetype" in names


class TestEPUBExporterSingleItem:
    def test_export_single_item(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="First Page",
                content="Hello world",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 1

    def test_export_single_item_produces_valid_epub(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="First Page",
                content="Hello world",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            assert "mimetype" in names
            assert "META-INF/container.xml" in names
            assert "content.opf" in names
            assert "nav.xhtml" in names

    def test_export_single_item_contains_title(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="My Special Title",
                content="Body text",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            nav = zf.read("nav.xhtml").decode("utf-8")
            assert "My Special Title" in nav


class TestEPUBExporterMultipleItems:
    def test_export_multiple_items(self):
        items = [
            EPUBContentItem(
                url="http://example.com/1",
                title="Chapter One",
                content="First chapter content",
            ),
            EPUBContentItem(
                url="http://example.com/2",
                title="Chapter Two",
                content="Second chapter content",
            ),
            EPUBContentItem(
                url="http://example.com/3",
                title="Chapter Three",
                content="Third chapter content",
            ),
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 3

    def test_export_multiple_items_has_chapters(self):
        items = [
            EPUBContentItem(
                url="http://example.com/1",
                title="Chapter One",
                content="First",
            ),
            EPUBContentItem(
                url="http://example.com/2",
                title="Chapter Two",
                content="Second",
            ),
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            # Should have chapter files
            chapter_files = [n for n in names if n.startswith("chapter_")]
            assert len(chapter_files) == 2

    def test_export_multiple_items_nav_has_all_titles(self):
        items = [
            EPUBContentItem(url="http://a.com", title="Alpha", content="A"),
            EPUBContentItem(url="http://b.com", title="Beta", content="B"),
            EPUBContentItem(url="http://c.com", title="Gamma", content="C"),
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            nav = zf.read("nav.xhtml").decode("utf-8")
            assert "Alpha" in nav
            assert "Beta" in nav
            assert "Gamma" in nav


class TestEPUBExporterConfig:
    def test_export_with_custom_title(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        config = EPUBExportConfig(title="Custom Book Title")
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            opf = zf.read("content.opf").decode("utf-8")
            assert "Custom Book Title" in opf

    def test_export_with_custom_author(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        config = EPUBExportConfig(author="Custom Author")
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            opf = zf.read("content.opf").decode("utf-8")
            assert "Custom Author" in opf

    def test_export_without_cover(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        config = EPUBExportConfig(include_cover=False)
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            assert "cover.xhtml" not in names

    def test_export_with_cover(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        config = EPUBExportConfig(include_cover=True)
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            assert "cover.xhtml" in names

    def test_export_without_toc(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        config = EPUBExportConfig(include_toc=False)
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            opf = zf.read("content.opf").decode("utf-8")
            # nav should not be in the spine when toc is disabled
            assert "nav.xhtml" not in opf or 'id="nav"' not in opf

    def test_export_with_text_chapter_format(self):
        items = [
            EPUBContentItem(
                url="http://x.com", title="Page", content="Body with <html>"
            )
        ]
        config = EPUBExportConfig(chapter_format=EPUBChapterFormat.TEXT)
        exporter = EPUBExporter(config=config)
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            chapter_files = [n for n in zf.namelist() if n.startswith("chapter_")]
            assert len(chapter_files) == 1
            chapter_content = zf.read(chapter_files[0]).decode("utf-8")
            # Text format should not have HTML tags
            assert "<html xmlns" not in chapter_content and "<head>" not in chapter_content
            assert "Body with <html>" in chapter_content


class TestEPUBExporterFromDicts:
    def test_export_from_dicts(self):
        items = [
            {"url": "http://a.com", "title": "Alpha", "content": "A content"},
            {"url": "http://b.com", "title": "Beta", "content": "B content"},
        ]
        exporter = EPUBExporter()
        result = exporter.export_from_dicts(items)
        assert result.success is True
        assert result.items_exported == 2

    def test_export_from_dicts_with_extra_fields(self):
        items = [
            {
                "url": "http://a.com",
                "title": "Full",
                "content": "Body",
                "word_count": 42,
                "category": "tech",
                "tags": ["python"],
                "created_at": "2024-01-01",
            }
        ]
        exporter = EPUBExporter()
        result = exporter.export_from_dicts(items)
        assert result.success is True
        assert result.items_exported == 1

    def test_export_from_dicts_missing_optional_fields(self):
        items = [{"url": "http://a.com"}]
        exporter = EPUBExporter()
        result = exporter.export_from_dicts(items)
        assert result.success is True
        assert result.items_exported == 1


class TestEPUBExporterEdgeCases:
    def test_export_unicode_content(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="日本語タイトル",
                content="これはテスト内容です",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 1

    def test_export_empty_content(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="Empty",
                content="",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 1

    def test_export_very_long_title(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title="A" * 500,
                content="Body",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True

    def test_export_special_characters_in_title(self):
        items = [
            EPUBContentItem(
                url="http://example.com",
                title='Title with "quotes" & <angles>',
                content="Body",
            )
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            opf = zf.read("content.opf").decode("utf-8")
            # Should be properly escaped
            assert "<angles>" not in opf

    def test_export_many_items(self):
        items = [
            EPUBContentItem(
                url=f"http://example.com/{i}",
                title=f"Chapter {i}",
                content=f"Content for chapter {i}",
            )
            for i in range(50)
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 50

    def test_export_mimetype_is_first(self):
        """EPUB spec requires mimetype file to be first and uncompressed."""
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            names = zf.namelist()
            assert names[0] == "mimetype"
            # mimetype should be stored (uncompressed)
            info = zf.getinfo("mimetype")
            assert info.compress_type == zipfile.ZIP_STORED

    def test_export_container_xml_is_valid(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            container = zf.read("META-INF/container.xml").decode("utf-8")
            assert "<?xml" in container
            assert "container" in container
            assert "content.opf" in container

    def test_export_content_opf_has_manifest(self):
        items = [
            EPUBContentItem(url="http://x.com", title="Page", content="Body")
        ]
        exporter = EPUBExporter()
        result = exporter.export(items)
        with zipfile.ZipFile(io.BytesIO(result.output)) as zf:
            opf = zf.read("content.opf").decode("utf-8")
            assert "<manifest>" in opf
            assert "<spine>" in opf
            assert "<metadata" in opf
