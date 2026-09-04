"""Tests for the formatter module."""

from personal_index.formatter import (
    format_crawl_stats,
    format_duration,
    format_file_size,
    format_index_page,
    format_interest,
    format_schedule_job,
    format_search_results,
    format_table,
    format_timestamp,
    highlight,
    truncate,
)
from personal_index.index import SearchResult
from personal_index.interests import Interest
from personal_index.scheduler import ScheduledJob


class TestFormatSearchResults:
    def test_empty_results(self):
        result = format_search_results([])
        assert "No results" in result

    def test_single_result(self):
        results = [SearchResult(
            url="https://example.com",
            title="Test Page",
            snippet="Test content",
            relevance_score=1.5,
        )]
        output = format_search_results(results)
        assert "Test Page" in output
        assert "https://example.com" in output
        assert "1.50" in output

    def test_multiple_results(self):
        results = [
            SearchResult(url="https://a.com", title="A", snippet="", relevance_score=1.0),
            SearchResult(url="https://b.com", title="B", snippet="", relevance_score=0.5),
        ]
        output = format_search_results(results)
        assert "1. A" in output
        assert "2. B" in output

    def test_limit_results(self):
        results = [
            SearchResult(url=f"https://{i}.com", title=str(i), snippet="", relevance_score=float(i))
            for i in range(30)
        ]
        output = format_search_results(results, limit=5)
        assert "6." not in output


class TestFormatInterest:
    def test_basic_interest(self):
        interest = Interest(name="python", keywords=["python"], enabled=True)
        output = format_interest(interest)
        assert "python" in output
        assert "enabled" in output

    def test_interest_with_topics(self):
        interest = Interest(name="ai", topics=["ML", "DL"], enabled=False)
        output = format_interest(interest)
        assert "disabled" in output
        assert "ML" in output


class TestFormatCrawlStats:
    def test_basic_stats(self):
        stats = {"pages_crawled": 10, "pages_indexed": 5, "pages_filtered": 3, "errors": 2}
        output = format_crawl_stats(stats)
        assert "10" in output
        assert "5" in output
        assert "3" in output
        assert "2" in output

    def test_empty_stats(self):
        stats = {}
        output = format_crawl_stats(stats)
        assert "0" in output


class TestFormatIndexPage:
    def test_basic_page(self):
        from personal_index.index import IndexedPage
        page = IndexedPage(
            url="https://example.com",
            title="Test Page",
            content="Test content",
            keywords=["test"],
            score=1.5,
            indexed_at="2024-01-01T00:00:00",
            word_count=10,
        )
        output = format_index_page(page)
        assert "Test Page" in output
        assert "1.50" in output


class TestFormatScheduleJob:
    def test_basic_job(self):
        job = ScheduledJob(
            name="daily",
            seed_urls=["https://example.com"],
            interval_hours=24,
            run_count=5,
            last_run="2024-01-01T00:00:00",
        )
        output = format_schedule_job(job)
        assert "daily" in output
        assert "24 hours" in output
        assert "5" in output


class TestFormatTable:
    def test_basic_table(self):
        headers = ["Name", "Score"]
        rows = [["Alice", "100"], ["Bob", "90"]]
        output = format_table(headers, rows)
        assert "Name" in output
        assert "Alice" in output
        assert "Bob" in output

    def test_empty_table(self):
        output = format_table([], [])
        assert output == ""

    def test_no_rows(self):
        output = format_table(["Name"], [])
        assert output == ""


class TestFormatDuration:
    def test_seconds(self):
        assert format_duration(30.5) == "30.5s"

    def test_minutes(self):
        assert format_duration(120) == "2.0m"

    def test_hours(self):
        assert format_duration(7200) == "2.0h"


class TestFormatFileSize:
    def test_bytes(self):
        assert format_file_size(500) == "500B"

    def test_kilobytes(self):
        assert format_file_size(1500) == "1.5KB"

    def test_megabytes(self):
        assert format_file_size(1500000) == "1.4MB"

    def test_gigabytes(self):
        assert format_file_size(1500000000) == "1.4GB"


class TestFormatTimestamp:
    def test_valid_timestamp(self):
        result = format_timestamp("2024-01-15T10:30:00")
        assert "2024-01-15" in result

    def test_empty_timestamp(self):
        assert format_timestamp("") == "N/A"
        assert format_timestamp(None) == "N/A"

    def test_invalid_timestamp(self):
        result = format_timestamp("not-a-date")
        assert result == "not-a-date"


class TestTruncate:
    def test_no_truncation(self):
        assert truncate("Short", max_length=20) == "Short"

    def test_truncation(self):
        result = truncate("A" * 100, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")


class TestHighlight:
    def test_basic_highlight(self):
        result = highlight("Hello world", ["world"])
        assert "**world**" in result

    def test_no_match(self):
        result = highlight("Hello world", ["foo"])
        assert result == "Hello world"

    def test_empty_terms(self):
        result = highlight("Hello world", [])
        assert result == "Hello world"

    def test_substring_terms(self):
        # A term that is a substring of another must not be re-matched
        # inside the longer term's inserted markers.
        assert highlight("cat catalog", ["cat", "catalog"]) == "**cat** **catalog**"
        assert highlight("pythonic code", ["python", "pythonic"]) == "**pythonic** code"
