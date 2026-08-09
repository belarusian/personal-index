"""Tests for content report generation module."""

import pytest
from personal_index.content_report import (
    ContentReport,
    ContentReportGenerator,
    ReportSection,
    ReportFormat,
    ReportFilter,
)


class TestReportSection:
    def test_create_section(self):
        s = ReportSection(title="Overview", content="Some content")
        assert s.title == "Overview"
        assert s.content == "Some content"

    def test_section_with_data(self):
        s = ReportSection(
            title="Stats",
            content="Statistics",
            data={"total": 100},
        )
        assert s.data["total"] == 100

    def test_section_to_dict(self):
        s = ReportSection(
            title="Overview",
            content="Content here",
            data={"items": 50},
        )
        d = s.to_dict()
        assert d["title"] == "Overview"
        assert d["content"] == "Content here"
        assert d["data"]["items"] == 50


class TestReportFormat:
    def test_format_values(self):
        assert ReportFormat.TEXT.value == "text"
        assert ReportFormat.MARKDOWN.value == "markdown"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.JSON.value == "json"


class TestReportFilter:
    def test_default_filter(self):
        f = ReportFilter()
        assert f.min_word_count is None
        assert f.max_word_count is None
        assert f.categories == []

    def test_custom_filter(self):
        f = ReportFilter(
            min_word_count=100,
            max_word_count=1000,
            categories=["Tech", "Science"],
            min_engagement=5.0,
        )
        assert f.min_word_count == 100
        assert f.max_word_count == 1000
        assert f.categories == ["Tech", "Science"]
        assert f.min_engagement == 5.0

    def test_filter_matches_word_count(self):
        f = ReportFilter(min_word_count=50, max_word_count=500)
        assert f.matches_word_count(100) is True
        assert f.matches_word_count(10) is False
        assert f.matches_word_count(1000) is False

    def test_filter_matches_category(self):
        f = ReportFilter(categories=["Tech", "Science"])
        assert f.matches_category("Tech") is True
        assert f.matches_category("Sports") is False

    def test_filter_matches_engagement(self):
        f = ReportFilter(min_engagement=5.0)
        assert f.matches_engagement(10.0) is True
        assert f.matches_engagement(2.0) is False

    def test_filter_matches_all(self):
        f = ReportFilter(
            min_word_count=50,
            categories=["Tech"],
            min_engagement=5.0,
        )
        assert f.matches_all(100, "Tech", 10.0) is True
        assert f.matches_all(100, "Sports", 10.0) is False
        assert f.matches_all(10, "Tech", 10.0) is False


class TestContentReport:
    def test_create_report(self):
        report = ContentReport(title="Test Report")
        assert report.title == "Test Report"
        assert report.format == "text"
        assert len(report.sections) == 0
        assert "generated_at" in report.to_dict()

    def test_add_section(self):
        report = ContentReport(title="Test")
        report.add_section(ReportSection(title="S1", content="C1"))
        assert len(report.sections) == 1

    def test_to_text(self):
        report = ContentReport(title="Test Report")
        report.add_section(ReportSection(
            title="Overview",
            content="Some content",
            data={"items": 10},
        ))
        text = report.to_text()
        assert "# Test Report" in text
        assert "## Overview" in text
        assert "items: 10" in text

    def test_to_markdown(self):
        report = ContentReport(title="Test Report", format=ReportFormat.MARKDOWN.value)
        report.add_section(ReportSection(
            title="Stats",
            content="Statistics",
            data={"total": 100},
        ))
        md = report.to_markdown()
        assert "# Test Report" in md
        assert "| Key | Value |" in md
        assert "| total | 100 |" in md

    def test_to_html(self):
        report = ContentReport(title="Test Report", format=ReportFormat.HTML.value)
        report.add_section(ReportSection(
            title="Overview",
            content="Content",
            data={"count": 5},
        ))
        html = report.to_html()
        assert "<!DOCTYPE html>" in html
        assert "<h1>Test Report</h1>" in html
        assert "<h2>Overview</h2>" in html
        assert "<td>count</td><td>5</td>" in html

    def test_render_default_text(self):
        report = ContentReport(title="Test")
        report.add_section(ReportSection(title="S1", content="C1"))
        text = report.render()
        assert "# Test" in text

    def test_render_markdown(self):
        report = ContentReport(title="Test", format=ReportFormat.MARKDOWN.value)
        report.add_section(ReportSection(title="S1", content="C1"))
        md = report.render()
        assert "# Test" in md

    def test_render_html(self):
        report = ContentReport(title="Test", format=ReportFormat.HTML.value)
        report.add_section(ReportSection(title="S1", content="C1"))
        html = report.render()
        assert "<!DOCTYPE html>" in html

    def test_render_json(self):
        report = ContentReport(title="Test", format=ReportFormat.JSON.value)
        report.add_section(ReportSection(title="S1", content="C1"))
        import json
        data = json.loads(report.render())
        assert data["title"] == "Test"
        assert len(data["sections"]) == 1

    def test_to_dict(self):
        report = ContentReport(title="Test")
        report.add_section(ReportSection(title="S1", content="C1", data={"x": 1}))
        d = report.to_dict()
        assert d["title"] == "Test"
        assert len(d["sections"]) == 1
        assert d["sections"][0]["data"]["x"] == 1


class TestContentReportGenerator:
    def test_add_items(self):
        gen = ContentReportGenerator()
        gen.add_items([{"url": "https://a.com", "title": "A"}])
        assert len(gen._items) == 1

    def test_generate_summary_report(self):
        gen = ContentReportGenerator()
        gen.add_items([
            {"url": "https://a.com", "title": "A", "word_count": 100, "category": "Tech", "engagement_score": 10.0},
            {"url": "https://b.com", "title": "B", "word_count": 200, "category": "Science", "engagement_score": 20.0},
        ])
        report = gen.generate_summary_report()
        assert report.title == "Content Summary Report"
        assert len(report.sections) >= 2

    def test_generate_report_with_filter(self):
        gen = ContentReportGenerator()
        gen.add_items([
            {"url": "https://a.com", "title": "A", "word_count": 100, "category": "Tech", "engagement_score": 10.0},
            {"url": "https://b.com", "title": "B", "word_count": 200, "category": "Sports", "engagement_score": 5.0},
        ])
        report = gen.generate_summary_report(
            filter=ReportFilter(categories=["Tech"])
        )
        # Only Tech items should be in the report
        overview = report.sections[0]
        assert overview.data["total_items"] == 1

    def test_generate_report_empty(self):
        gen = ContentReportGenerator()
        report = gen.generate_summary_report()
        assert report.title == "Content Summary Report"
        assert len(report.sections) >= 1

    def test_generate_report_custom_format(self):
        gen = ContentReportGenerator()
        gen.add_items([
            {"url": "https://a.com", "title": "A", "word_count": 100, "category": "Tech"},
        ])
        report = gen.generate_summary_report(fmt=ReportFormat.MARKDOWN)
        assert report.format == "markdown"
        md = report.render()
        assert "# Content Summary Report" in md

    def test_generate_report_top_items(self):
        gen = ContentReportGenerator()
        for i in range(15):
            gen.add_items([{
                "url": f"https://{i}.com",
                "title": f"Page {i}",
                "word_count": 100,
                "category": "Tech",
                "engagement_score": float(i * 10),
            }])
        report = gen.generate_summary_report()
        # Should have a "Top Engaged Content" section
        top_section = None
        for s in report.sections:
            if "Top" in s.title:
                top_section = s
                break
        assert top_section is not None
        assert len(top_section.data) == 10  # Top 10


class TestReportAdvanced:
    def test_report_with_multiple_sections(self):
        report = ContentReport(title="Multi Section")
        for i in range(5):
            report.add_section(ReportSection(
                title=f"Section {i}",
                content=f"Content {i}",
                data={"index": i},
            ))
        assert len(report.sections) == 5
        text = report.to_text()
        for i in range(5):
            assert f"## Section {i}" in text

    def test_report_metadata(self):
        report = ContentReport(
            title="Test",
            metadata={"author": "test", "version": "1.0"},
        )
        d = report.to_dict()
        assert d["metadata"]["author"] == "test"

    def test_report_generator_multiple_categories(self):
        gen = ContentReportGenerator()
        categories = ["Tech", "Science", "Sports", "News", "Finance"]
        for cat in categories:
            for i in range(3):
                gen.add_items([{
                    "url": f"https://{cat}{i}.com",
                    "title": f"{cat} {i}",
                    "word_count": 100,
                    "category": cat,
                    "engagement_score": float(i),
                }])
        report = gen.generate_summary_report()
        cat_section = None
        for s in report.sections:
            if "Category" in s.title:
                cat_section = s
                break
        assert cat_section is not None
        assert len(cat_section.data) == 5

    def test_report_generator_filter_by_engagement(self):
        gen = ContentReportGenerator()
        gen.add_items([
            {"url": "https://a.com", "title": "A", "word_count": 100,
             "category": "Tech", "engagement_score": 1.0},
            {"url": "https://b.com", "title": "B", "word_count": 200,
             "category": "Tech", "engagement_score": 25.0},
            {"url": "https://c.com", "title": "C", "word_count": 150,
             "category": "Tech", "engagement_score": 50.0},
        ])
        report = gen.generate_summary_report(
            filter=ReportFilter(min_engagement=10.0)
        )
        overview = report.sections[0]
        assert overview.data["total_items"] == 2

    def test_report_generator_filter_by_word_count_range(self):
        gen = ContentReportGenerator()
        gen.add_items([
            {"url": "https://a.com", "title": "A", "word_count": 50,
             "category": "Tech", "engagement_score": 10.0},
            {"url": "https://b.com", "title": "B", "word_count": 200,
             "category": "Tech", "engagement_score": 10.0},
            {"url": "https://c.com", "title": "C", "word_count": 1000,
             "category": "Tech", "engagement_score": 10.0},
        ])
        report = gen.generate_summary_report(
            filter=ReportFilter(min_word_count=100, max_word_count=500)
        )
        overview = report.sections[0]
        assert overview.data["total_items"] == 1
