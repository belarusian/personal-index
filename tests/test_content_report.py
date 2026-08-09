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
