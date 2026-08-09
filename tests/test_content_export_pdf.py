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


class TestPDFExportResult:
    def test_default_result(self):
        result = PDFExportResult()
        assert result.success is True
        assert result.items_exported == 0
        assert result.total_pages == 0
        assert result.output is None
        assert result.errors == []

    def test_result_to_dict(self):
        result = PDFExportResult(
            success=True,
            items_exported=10,
            total_pages=2,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["items_exported"] == 10
        assert d["total_pages"] == 2
        assert "exported_at" in d

    def test_failed_result(self):
        result = PDFExportResult(
            success=False,
            errors=["Something went wrong"],
        )
        assert result.success is False
        assert len(result.errors) == 1


class TestPDFExporter:
    def test_export_empty(self):
        exporter = PDFExporter()
        result = exporter.export([])
        assert result.success is True
        assert result.items_exported == 0
        assert result.total_pages == 0

    def test_export_single_item(self):
        exporter = PDFExporter()
        items = [PDFContentItem(
            url="https://example.com",
            title="Example",
            content="Hello world",
            word_count=2,
        )]
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 1
        assert result.total_pages == 1
        assert "Example" in result.output

    def test_export_multiple_items(self):
        exporter = PDFExporter()
        items = [
            PDFContentItem(url=f"https://{i}.com", title=f"Page {i}", content=f"Content {i}")
            for i in range(25)
        ]
        result = exporter.export(items)
        assert result.success is True
        assert result.items_exported == 25
        assert result.total_pages == 3  # 25 items / 10 per page

    def test_export_with_cover(self):
        exporter = PDFExporter()
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "=" * 60 in result.output

    def test_export_without_cover(self):
        config = PDFExportConfig(include_cover=False)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "Content Export" not in result.output

    def test_export_without_toc(self):
        config = PDFExportConfig(include_toc=False)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "TABLE OF CONTENTS" not in result.output

    def test_export_sorted_by_title(self):
        config = PDFExportConfig(sort_by="title", sort_reverse=False)
        exporter = PDFExporter(config=config)
        items = [
            PDFContentItem(url="https://c.com", title="Charlie"),
            PDFContentItem(url="https://a.com", title="Alpha"),
            PDFContentItem(url="https://b.com", title="Bravo"),
        ]
        result = exporter.export(items)
        # Alpha should appear before Bravo in output
        alpha_pos = result.output.index("Alpha")
        bravo_pos = result.output.index("Bravo")
        assert alpha_pos < bravo_pos

    def test_export_sorted_by_word_count(self):
        config = PDFExportConfig(sort_by="word_count", sort_reverse=True)
        exporter = PDFExporter(config=config)
        items = [
            PDFContentItem(url="https://a.com", title="A", word_count=100),
            PDFContentItem(url="https://b.com", title="B", word_count=500),
            PDFContentItem(url="https://c.com", title="C", word_count=200),
        ]
        result = exporter.export(items)
        # B (500) should appear first
        b_pos = result.output.index("## B")
        c_pos = result.output.index("## C")
        a_pos = result.output.index("## A")
        assert b_pos < c_pos < a_pos

    def test_export_from_dicts(self):
        exporter = PDFExporter()
        items = [
            {"url": "https://a.com", "title": "Page A", "content": "Hello", "word_count": 1},
            {"url": "https://b.com", "title": "Page B", "content": "World", "word_count": 1},
        ]
        result = exporter.export_from_dicts(items)
        assert result.success is True
        assert result.items_exported == 2

    def test_export_custom_items_per_page(self):
        config = PDFExportConfig(items_per_page=5)
        exporter = PDFExporter(config=config)
        items = [
            PDFContentItem(url=f"https://{i}.com", title=f"P{i}")
            for i in range(12)
        ]
        result = exporter.export(items)
        assert result.total_pages == 3  # 12 / 5 = 3 pages

    def test_export_with_engagement_score(self):
        exporter = PDFExporter()
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            engagement_score=15.5,
        )]
        result = exporter.export(items)
        assert "Engagement score: 15.5" in result.output

    def test_export_with_tags(self):
        exporter = PDFExporter()
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            tags=["python", "web"],
        )]
        result = exporter.export(items)
        assert "Tags: python, web" in result.output

    def test_export_with_category(self):
        exporter = PDFExporter()
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            category="Technology",
        )]
        result = exporter.export(items)
        assert "Category: Technology" in result.output

    def test_export_with_timestamp(self):
        exporter = PDFExporter()
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            created_at="2024-01-15T10:30:00Z",
        )]
        result = exporter.export(items)
        assert "Saved: 2024-01-15T10:30:00Z" in result.output

    def test_export_without_word_counts(self):
        config = PDFExportConfig(include_word_counts=False)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            word_count=100,
        )]
        result = exporter.export(items)
        assert "Word count:" not in result.output

    def test_export_without_timestamps(self):
        config = PDFExportConfig(include_timestamps=False)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(
            url="https://a.com",
            title="A",
            created_at="2024-01-15T10:30:00Z",
        )]
        result = exporter.export(items)
        assert "Saved:" not in result.output


class TestPDFExporterAdvanced:
    def test_export_legal_layout(self):
        config = PDFExportConfig(page_layout=PDFPageLayout.LEGAL)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "LEGAL" in result.output

    def test_export_letter_layout(self):
        config = PDFExportConfig(page_layout=PDFPageLayout.LETTER)
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "LETTER" in result.output

    def test_export_sorted_by_category(self):
        config = PDFExportConfig(sort_by="category", sort_reverse=False)
        exporter = PDFExporter(config=config)
        items = [
            PDFContentItem(url="https://c.com", title="C", category="Zebra"),
            PDFContentItem(url="https://a.com", title="A", category="Alpha"),
            PDFContentItem(url="https://b.com", title="B", category="Beta"),
        ]
        result = exporter.export(items)
        alpha_pos = result.output.index("## A")
        beta_pos = result.output.index("## B")
        zebra_pos = result.output.index("## C")
        assert alpha_pos < beta_pos < zebra_pos

    def test_export_sorted_by_engagement(self):
        config = PDFExportConfig(sort_by="engagement_score", sort_reverse=True)
        exporter = PDFExporter(config=config)
        items = [
            PDFContentItem(url="https://a.com", title="A", engagement_score=5.0),
            PDFContentItem(url="https://b.com", title="B", engagement_score=50.0),
            PDFContentItem(url="https://c.com", title="C", engagement_score=25.0),
        ]
        result = exporter.export(items)
        b_pos = result.output.index("## B")
        c_pos = result.output.index("## C")
        a_pos = result.output.index("## A")
        assert b_pos < c_pos < a_pos

    def test_export_from_dicts_with_all_fields(self):
        exporter = PDFExporter()
        items = [{
            "url": "https://a.com",
            "title": "Full Item",
            "content": "Some content here",
            "word_count": 4,
            "category": "Tech",
            "tags": ["python", "web"],
            "created_at": "2024-01-01T00:00:00Z",
            "engagement_score": 15.0,
        }]
        result = exporter.export_from_dicts(items)
        assert result.success is True
        assert "Full Item" in result.output
        assert "Category: Tech" in result.output
        assert "Tags: python, web" in result.output
        assert "Saved: 2024-01-01T00:00:00Z" in result.output
        assert "Engagement score: 15.0" in result.output

    def test_export_empty_dicts(self):
        exporter = PDFExporter()
        result = exporter.export_from_dicts([])
        assert result.success is True
        assert result.items_exported == 0

    def test_export_result_to_dict(self):
        exporter = PDFExporter()
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        d = result.to_dict()
        assert d["success"] is True
        assert d["items_exported"] == 1
        assert "exported_at" in d
        assert d["errors"] == []

    def test_export_with_custom_title(self):
        config = PDFExportConfig(title="My Custom Report")
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "My Custom Report" in result.output

    def test_export_with_custom_author(self):
        config = PDFExportConfig(author="Jane Doe")
        exporter = PDFExporter(config=config)
        items = [PDFContentItem(url="https://a.com", title="A")]
        result = exporter.export(items)
        assert "Jane Doe" in result.output

    def test_export_pagination_boundaries(self):
        """Test exact page boundaries."""
        config = PDFExportConfig(items_per_page=5)
        exporter = PDFExporter(config=config)
        # Exactly 10 items = 2 pages
        items = [
            PDFContentItem(url=f"https://{i}.com", title=f"P{i}")
            for i in range(10)
        ]
        result = exporter.export(items)
        assert result.total_pages == 2

        # 11 items = 3 pages
        items.append(PDFContentItem(url="https://11.com", title="P11"))
        result = exporter.export(items)
        assert result.total_pages == 3
