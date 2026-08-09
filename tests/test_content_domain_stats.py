"""Tests for content_domain_stats module - per-domain save statistics."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_domain_stats import (
    DomainStats,
    DomainStatsManager,
)


class TestDomainStats:
    """Tests for DomainStats dataclass."""

    def test_create_domain_stats_basic(self):
        ds = DomainStats(domain="example.com")
        assert ds.domain == "example.com"
        assert ds.total_saves == 0
        assert ds.unique_urls == 0
        assert ds.total_size_bytes == 0
        assert ds.created_at is not None

    def test_create_domain_stats_with_values(self):
        ds = DomainStats(
            domain="example.com",
            total_saves=10,
            unique_urls=5,
            total_size_bytes=1024,
        )
        assert ds.total_saves == 10
        assert ds.unique_urls == 5
        assert ds.total_size_bytes == 1024

    def test_create_domain_stats_with_tags(self):
        ds = DomainStats(
            domain="example.com",
            top_tags=["tech", "news"],
        )
        assert ds.top_tags == ["tech", "news"]

    def test_create_domain_stats_with_status_codes(self):
        ds = DomainStats(
            domain="example.com",
            status_codes={"200": 8, "404": 2},
        )
        assert ds.status_codes == {"200": 8, "404": 2}

    def test_domain_stats_to_dict(self):
        ds = DomainStats(
            domain="example.com",
            total_saves=10,
            unique_urls=5,
            total_size_bytes=1024,
        )
        d = ds.to_dict()
        assert d["domain"] == "example.com"
        assert d["total_saves"] == 10
        assert d["unique_urls"] == 5

    def test_domain_stats_from_dict(self):
        data = {
            "domain": "example.com",
            "total_saves": 20,
            "unique_urls": 10,
            "total_size_bytes": 2048,
            "last_saved_at": "2024-01-01T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00",
            "top_tags": ["tech"],
            "status_codes": {"200": 15, "404": 5},
            "avg_response_time_ms": 150,
        }
        ds = DomainStats.from_dict(data)
        assert ds.domain == "example.com"
        assert ds.total_saves == 20
        assert ds.unique_urls == 10
        assert ds.top_tags == ["tech"]
        assert ds.status_codes == {"200": 15, "404": 5}
        assert ds.avg_response_time_ms == 150

    def test_domain_stats_from_dict_defaults(self):
        data = {"domain": "example.com"}
        ds = DomainStats.from_dict(data)
        assert ds.total_saves == 0
        assert ds.unique_urls == 0
        assert ds.top_tags == []

    def test_domain_stats_record_save(self):
        ds = DomainStats(domain="example.com")
        ds.record_save(size_bytes=512)
        assert ds.total_saves == 1
        assert ds.total_size_bytes == 512

    def test_domain_stats_record_save_multiple(self):
        ds = DomainStats(domain="example.com")
        ds.record_save(size_bytes=100)
        ds.record_save(size_bytes=200)
        assert ds.total_saves == 2
        assert ds.total_size_bytes == 300

    def test_domain_stats_add_url(self):
        ds = DomainStats(domain="example.com")
        ds.add_url("https://example.com/page1")
        ds.add_url("https://example.com/page2")
        assert ds.unique_urls == 2

    def test_domain_stats_add_duplicate_url(self):
        ds = DomainStats(domain="example.com")
        ds.add_url("https://example.com/page1")
        ds.add_url("https://example.com/page1")
        assert ds.unique_urls == 1

    def test_domain_stats_add_tag(self):
        ds = DomainStats(domain="example.com")
        ds.add_tag("tech")
        ds.add_tag("news")
        assert "tech" in ds.top_tags
        assert "news" in ds.top_tags

    def test_domain_stats_add_duplicate_tag(self):
        ds = DomainStats(domain="domain.com")
        ds.add_tag("tech")
        ds.add_tag("tech")
        assert ds.top_tags.count("tech") == 1

    def test_domain_stats_record_status_code(self):
        ds = DomainStats(domain="example.com")
        ds.record_status_code(200)
        ds.record_status_code(404)
        assert ds.status_codes["200"] == 1
        assert ds.status_codes["404"] == 1

    def test_domain_stats_update_response_time(self):
        ds = DomainStats(domain="example.com")
        ds.update_response_time(100)
        assert ds.avg_response_time_ms == 100
        ds.update_response_time(200)
        assert ds.avg_response_time_ms == 150

    def test_domain_stats_get_formatted_size(self):
        ds = DomainStats(domain="example.com", total_size_bytes=1024)
        assert ds.get_formatted_size() == "1.00 KB"

    def test_domain_stats_get_formatted_size_bytes(self):
        ds = DomainStats(domain="example.com", total_size_bytes=500)
        assert ds.get_formatted_size() == "500.00 B"

    def test_domain_stats_get_formatted_size_mb(self):
        ds = DomainStats(domain="example.com", total_size_bytes=1048576)
        assert ds.get_formatted_size() == "1.00 MB"

    def test_domain_stats_get_formatted_size_gb(self):
        ds = DomainStats(domain="example.com", total_size_bytes=1073741824)
        assert ds.get_formatted_size() == "1.00 GB"

    def test_domain_stats_get_save_rate(self):
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        ds = DomainStats(
            domain="example.com",
            total_saves=30,
            created_at=past,
        )
        rate = ds.get_save_rate()
        assert rate > 0

    def test_domain_stats_get_save_rate_no_time(self):
        ds = DomainStats(domain="example.com", total_saves=10)
        rate = ds.get_save_rate()
        assert rate >= 0

    def test_domain_stats_get_save_rate_zero(self):
        ds = DomainStats(domain="example.com", total_saves=0)
        rate = ds.get_save_rate()
        assert rate == 0


class TestDomainStatsManager:
    """Tests for DomainStatsManager class."""

    def test_get_or_create_domain(self):
        mgr = DomainStatsManager()
        ds = mgr.get_or_create_domain("example.com")
        assert ds.domain == "example.com"

    def test_get_or_create_existing(self):
        mgr = DomainStatsManager()
        ds1 = mgr.get_or_create_domain("example.com")
        ds2 = mgr.get_or_create_domain("example.com")
        assert ds1 is ds2

    def test_record_save(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page", size_bytes=1024)
        ds = mgr.get_or_create_domain("example.com")
        assert ds.total_saves == 1
        assert ds.total_size_bytes == 1024

    def test_record_save_with_url(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page1", size_bytes=100)
        mgr.record_save("https://example.com/page2", size_bytes=200)
        ds = mgr.get_or_create_domain("example.com")
        assert ds.unique_urls == 2

    def test_record_save_with_status_code(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page", status_code=200)
        ds = mgr.get_or_create_domain("example.com")
        assert ds.status_codes["200"] == 1

    def test_record_save_with_response_time(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page", response_time_ms=150)
        ds = mgr.get_or_create_domain("example.com")
        assert ds.avg_response_time_ms == 150

    def test_record_save_with_tags(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page", tags=["tech", "news"])
        ds = mgr.get_or_create_domain("example.com")
        assert "tech" in ds.top_tags
        assert "news" in ds.top_tags

    def test_get_domain_stats(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/page")
        ds = mgr.get_domain_stats("example.com")
        assert ds is not None
        assert ds.domain == "example.com"

    def test_get_domain_stats_not_found(self):
        mgr = DomainStatsManager()
        ds = mgr.get_domain_stats("unknown.com")
        assert ds is None

    def test_list_domains(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://other.com/b")
        domains = mgr.list_domains()
        assert len(domains) == 2

    def test_list_domains_sorted_by_saves(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://example.com/b")
        mgr.record_save("https://other.com/c")
        domains = mgr.list_domains(sort_by="saves")
        assert domains[0].domain == "example.com"

    def test_list_domains_sorted_by_size(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", size_bytes=100)
        mgr.record_save("https://other.com/b", size_bytes=1000)
        domains = mgr.list_domains(sort_by="size")
        assert domains[0].domain == "other.com"

    def test_get_domain_count(self):
        mgr = DomainStatsManager()
        assert mgr.get_domain_count() == 0
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://other.com/b")
        assert mgr.get_domain_count() == 2

    def test_get_total_saves(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://example.com/b")
        mgr.record_save("https://other.com/c")
        assert mgr.get_total_saves() == 3

    def test_get_total_size(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", size_bytes=100)
        mgr.record_save("https://other.com/b", size_bytes=200)
        assert mgr.get_total_size() == 300

    def test_get_top_domains(self):
        mgr = DomainStatsManager()
        for i in range(5):
            mgr.record_save(f"https://example.com/page{i}")
        for i in range(3):
            mgr.record_save(f"https://other.com/page{i}")
        for i in range(1):
            mgr.record_save(f"https://third.com/page{i}")
        top = mgr.get_top_domains(limit=2)
        assert len(top) == 2
        assert top[0].domain == "example.com"
        assert top[1].domain == "other.com"

    def test_get_domain_summary(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", size_bytes=100)
        mgr.record_save("https://other.com/b", size_bytes=200)
        summary = mgr.get_domain_summary()
        assert summary["total_domains"] == 2
        assert summary["total_saves"] == 2
        assert summary["total_size_bytes"] == 300

    def test_remove_domain(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        result = mgr.remove_domain("example.com")
        assert result is True
        assert mgr.get_domain_stats("example.com") is None

    def test_remove_domain_not_found(self):
        mgr = DomainStatsManager()
        result = mgr.remove_domain("unknown.com")
        assert result is False

    def test_reset_domain(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://example.com/b")
        mgr.reset_domain("example.com")
        ds = mgr.get_domain_stats("example.com")
        assert ds.total_saves == 0
        assert ds.unique_urls == 0

    def test_get_domains_by_tag(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", tags=["tech"])
        mgr.record_save("https://other.com/b", tags=["news"])
        mgr.record_save("https://third.com/c", tags=["tech"])
        tech_domains = mgr.get_domains_by_tag("tech")
        assert len(tech_domains) == 2

    def test_get_save_history(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://example.com/b")
        history = mgr.get_save_history("example.com", limit=5)
        assert len(history) == 2

    def test_serialize_deserialize(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", size_bytes=100, tags=["tech"])
        data = mgr.to_dict()
        new_mgr = DomainStatsManager.from_dict(data)
        ds = new_mgr.get_domain_stats("example.com")
        assert ds is not None
        assert ds.total_saves == 1
        assert ds.total_size_bytes == 100
        assert "tech" in ds.top_tags

    def test_get_domains_with_errors(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a", status_code=200)
        mgr.record_save("https://other.com/b", status_code=404)
        mgr.record_save("https://third.com/c", status_code=500)
        error_domains = mgr.get_domains_with_errors()
        assert len(error_domains) == 2

    def test_get_domain_percentage(self):
        mgr = DomainStatsManager()
        mgr.record_save("https://example.com/a")
        mgr.record_save("https://example.com/b")
        mgr.record_save("https://other.com/c")
        pct = mgr.get_domain_percentage("example.com")
        assert pct == pytest.approx(66.67, abs=1)
