"""Tests for dashboard views module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from personal_index.dashboard.views import (
    DashboardData,
    DashboardSection,
    DashboardStat,
    build_dashboard,
    escape,
    render_dashboard_html,
)


class TestDashboardStat:
    """Tests for DashboardStat."""

    def test_to_dict(self):
        """Test stat serialization."""
        stat = DashboardStat(label="Pages", value=42, trend="+5")
        d = stat.to_dict()
        assert d["label"] == "Pages"
        assert d["value"] == 42
        assert d["trend"] == "+5"

    def test_default_values(self):
        """Test default stat values."""
        stat = DashboardStat(label="Test", value=0)
        assert stat.trend is None
        assert stat.icon == ""


class TestDashboardSection:
    """Tests for DashboardSection."""

    def test_to_dict_with_stats(self):
        """Test section serialization with stats."""
        section = DashboardSection(
            title="Overview",
            stats=[DashboardStat(label="Pages", value=10)],
        )
        d = section.to_dict()
        assert d["title"] == "Overview"
        assert len(d["stats"]) == 1
        assert d["table_data"] is None

    def test_to_dict_with_table(self):
        """Test section serialization with table data."""
        section = DashboardSection(
            title="Pages",
            table_data=[{"url": "http://example.com", "title": "Test"}],
        )
        d = section.to_dict()
        assert d["table_data"] is not None
        assert len(d["table_data"]) == 1


class TestDashboardData:
    """Tests for DashboardData."""

    def test_to_dict(self):
        """Test dashboard data serialization."""
        data = DashboardData(
            title="Test Dashboard",
            sections=[DashboardSection(title="Overview")],
        )
        d = data.to_dict()
        assert d["title"] == "Test Dashboard"
        assert len(d["sections"]) == 1
        assert "generated_at" in d
        assert d["version"] == "0.1.0"


class TestEscape:
    """Tests for HTML escaping."""

    def test_escapes_html(self):
        """Test HTML special characters are escaped."""
        assert escape("<script>") == "&lt;script&gt;"
        assert escape('"quotes"') == "&quot;quotes&quot;"
        assert escape("&amp;") == "&amp;amp;"

    def test_escapes_non_string(self):
        """Test escaping non-string values."""
        assert escape(123) == "123"
        assert escape(None) == "None"


class TestRenderDashboardHtml:
    """Tests for HTML rendering."""

    def test_renders_valid_html(self):
        """Test that valid HTML is rendered."""
        data = DashboardData(
            title="Test",
            sections=[
                DashboardSection(
                    title="Overview",
                    stats=[DashboardStat(label="Pages", value=42)],
                )
            ],
        )
        html_output = render_dashboard_html(data)
        assert "<!DOCTYPE html>" in html_output
        assert "Test" in html_output
        assert "42" in html_output
        assert "</html>" in html_output

    def test_escapes_user_content(self):
        """Test that user content is escaped in HTML."""
        data = DashboardData(
            title="<script>alert('xss')</script>",
            sections=[
                DashboardSection(
                    title="Test",
                    stats=[DashboardStat(label="<b>Bold</b>", value="<img>")],
                )
            ],
        )
        html_output = render_dashboard_html(data)
        assert "<script>" not in html_output
        assert "&lt;script&gt;" in html_output

    def test_renders_table_data(self):
        """Test that table data is rendered."""
        data = DashboardData(
            title="Test",
            sections=[
                DashboardSection(
                    title="Pages",
                    table_data=[
                        {"URL": "http://example.com", "Title": "Home"},
                    ],
                )
            ],
        )
        html_output = render_dashboard_html(data)
        assert "http://example.com" in html_output
        assert "<table>" in html_output

    def test_renders_trend(self):
        """Test that trend values are rendered."""
        data = DashboardData(
            title="Test",
            sections=[
                DashboardSection(
                    title="Stats",
                    stats=[DashboardStat(label="Growth", value=100, trend="+10%")],
                )
            ],
        )
        html_output = render_dashboard_html(data)
        assert "trend up" in html_output
        assert "+10%" in html_output


class TestBuildDashboard:
    """Tests for build_dashboard function."""

    def test_build_empty(self):
        """Test building dashboard with no instances."""
        data = build_dashboard()
        assert data.title == "Personal Index Dashboard"
        assert len(data.sections) >= 1

    def test_build_with_mock_index(self):
        """Test building dashboard with mock index."""
        mock_index = MagicMock()
        mock_index.get_all_pages.return_value = []
        mock_index.interests = []

        data = build_dashboard(index_instance=mock_index)
        assert len(data.sections) >= 1
        mock_index.get_all_pages.assert_called()

    def test_build_with_pages(self):
        """Test building dashboard with pages."""
        from personal_index.models import IndexedPage

        mock_index = MagicMock()
        pages = [
            IndexedPage(url="http://a.com", title="Page A", domain="a.com"),
            IndexedPage(url="http://b.com", title="Page B", domain="b.com"),
        ]
        mock_index.get_all_pages.return_value = pages
        mock_index.interests = []

        data = build_dashboard(index_instance=mock_index)
        # Should have overview, recent pages, and top domains sections
        assert len(data.sections) >= 3
