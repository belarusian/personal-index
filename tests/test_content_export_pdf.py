"""Tests for content PDF export module."""

import pytest
from personal_index.content_export_pdf import (
    PDFExportConfig,
    PDFExporter,
    PDFPageLayout,
    PDFContentItem,
    PDFExportResult,
)


class TestPDFExportConfig:
    def test_default_config(self):
        config = PDFExportConfig()
        assert config.title == "Content Export"
        assert config.author == "personal-index"
        assert config.page_layout == PDFPageLayout.A4
        assert config.include_cover == True
        assert config.include_toc == True
        assert config.items_per_page == 10

    def test_custom_config(self):
        config = PDFExportConfig(
            title="My Report",
            author="John Doe",
            page_layout=PDFPageLayout.LETTER,
            include_cover=False,
            include_toc=False,
            items_per_page=5,
        )
        assert config.title == "My Report"
        assert config.author == "John Doe"
        assert config.page_layout == PDFPageLayout.LETTER
        assert config.include_cover is False
        assert config.include_toc is False
        assert config.items_per_page == 5

    def test_config_to_dict(self):
        config = PDFExportConfig(title="Test")
        d = config.to_dict()
        assert d["title"] == "Test"
        assert d["author"] == "personal-index"


class TestPDFPageLayout:
    def test_layout_values(self):
        assert PDFPageLayout.A4.value == "a4"
        assert PDFPageLayout.LETTER.value == "letter"
        assert PDFPageLayout.LEGAL.value == "legal"

    def test_layout_dimensions(self):
        a4 = PDFPageLayout.A4
        assert a4.width_mm == 210
        assert a4.height_mm == 297

        letter = PDFPageLayout.LETTER
        assert letter.width_mm == 216
        assert letter.height_mm == 279


class TestPDFContentItem:
    def test_create_item(self):
        item = PDFContentItem(
            url="https://example.com",
            title="Example Page",
            content="Some content here",
            word_count=5,
        )
        assert item.url == "https://example.com"
        assert item.title == "Example Page"
        assert item.word_count == 5

    def test_item_default_content(self):
        item = PDFContentItem(url="https://example.com", title="Test")
        assert item.content == ""

    def test_item_to_dict(self):
        item = PDFContentItem(
            url="https://example.com",
            title="Test",
            content="Hello world",
            word_count=2,
        )
        d = item.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"
        assert d["word_count"] == 2

    def test_item_truncate_content(self):
        item = PDFContentItem(
            url="https://example.com",
            title="Test",
            content="A" * 1000,
        )
        truncated = item.truncate_content(100)
        assert len(truncated) <= 100
