"""Tests for personal_index.dashboard.aggregator module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from personal_index.dashboard.aggregator import (
    AggregatedStats,
    DashboardAggregator,
    TimeSeriesPoint,
)


@dataclass
class MockPage:
    """Mock page object for testing DashboardAggregator."""

    url: str = ""
    domain: str = ""
    content_type: str = ""
    status_code: int = 200
    relevance_score: float = 0.5
    crawled_at: str = ""
    keywords: list[str] | None = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


# ── TimeSeriesPoint tests ──────────────────────────────────────────────


class TestTimeSeriesPoint:
    """Tests for TimeSeriesPoint dataclass."""

    def test_to_dict_basic(self):
        """TimeSeriesPoint.to_dict() returns correct dict."""
        point = TimeSeriesPoint(timestamp="2024-01-01", value=42.0, label="test")
        result = point.to_dict()
        assert result == {
            "timestamp": "2024-01-01",
            "value": 42.0,
            "label": "test",
        }

    def test_to_dict_empty_label(self):
        """TimeSeriesPoint.to_dict() with empty label defaults to empty string."""
        point = TimeSeriesPoint(timestamp="2024-01-01", value=1.0)
        result = point.to_dict()
        assert result["label"] == ""

    def test_to_dict_zero_value(self):
        """TimeSeriesPoint.to_dict() handles zero value."""
        point = TimeSeriesPoint(timestamp="2024-01-01", value=0.0, label="zero")
        result = point.to_dict()
        assert result["value"] == 0.0


# ── AggregatedStats tests ──────────────────────────────────────────────


class TestAggregatedStats:
    """Tests for AggregatedStats dataclass."""

    def test_to_dict_defaults(self):
        """AggregatedStats.to_dict() with all defaults."""
        stats = AggregatedStats()
        result = stats.to_dict()
        assert result["total_pages"] == 0
        assert result["total_domains"] == 0
        assert result["total_interests"] == 0
        assert result["total_keywords"] == 0
        assert result["avg_relevance_score"] == 0.0
        assert result["pages_per_day"] == 0.0
        assert result["crawl_success_rate"] == 100.0
        assert result["top_domains"] == []
        assert result["recent_activity"] == []
        assert result["status_breakdown"] == {}
        assert result["content_type_breakdown"] == {}

    def test_to_dict_populated(self):
        """AggregatedStats.to_dict() with populated fields."""
        point = TimeSeriesPoint(timestamp="2024-01-01", value=5.0, label="2024-01-01")
        stats = AggregatedStats(
            total_pages=100,
            total_domains=10,
            total_interests=5,
            total_keywords=50,
            avg_relevance_score=0.756,
            pages_per_day=3.456,
            crawl_success_rate=95.67,
            top_domains=[{"domain": "example.com", "count": 10}],
            recent_activity=[point],
            status_breakdown={"2xx": 90, "4xx": 10},
            content_type_breakdown={"text/html": 80, "application/json": 20},
        )
        result = stats.to_dict()
        assert result["total_pages"] == 100
        assert result["total_domains"] == 10
        assert result["avg_relevance_score"] == 0.76  # rounded to 2 decimals
        assert result["pages_per_day"] == 3.5  # rounded to 1 decimal
        assert result["crawl_success_rate"] == 95.7  # rounded to 1 decimal
        assert len(result["recent_activity"]) == 1
        assert result["recent_activity"][0]["timestamp"] == "2024-01-01"
        assert result["status_breakdown"] == {"2xx": 90, "4xx": 10}
        assert result["content_type_breakdown"] == {"text/html": 80, "application/json": 20}


# ── DashboardAggregator tests ──────────────────────────────────────────


class TestDashboardAggregatorInit:
    """Tests for DashboardAggregator initialization."""

    def test_init_defaults(self):
        """DashboardAggregator initializes with None cache and zero cache_time."""
        agg = DashboardAggregator()
        assert agg._cached_stats is None
        assert agg._cache_time == 0.0
        assert agg._cache_ttl == 30.0


class TestDashboardAggregatorAggregate:
    """Tests for DashboardAggregator.aggregate()."""

    def _make_pages(self, n: int = 3) -> list[MockPage]:
        """Create a list of MockPage instances."""
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return [
            MockPage(
                url=f"https://example{i}.com/page",
                domain=f"example{i}.com",
                content_type="text/html",
                status_code=200,
                relevance_score=0.5 + i * 0.1,
                crawled_at=(base + timedelta(days=i)).isoformat(),
                keywords=[f"kw{i}", "shared"],
            )
            for i in range(n)
        ]

    def test_aggregate_no_index(self):
        """aggregate() with no index returns empty stats."""
        agg = DashboardAggregator()
        stats = agg.aggregate()
        assert stats.total_pages == 0
        assert stats.total_domains == 0
        assert stats.total_keywords == 0

    def test_aggregate_with_mock_index(self):
        """aggregate() with mock index populates stats."""
        pages = self._make_pages(3)
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = ["python", "web"]

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)

        assert stats.total_pages == 3
        assert stats.total_domains == 3
        assert stats.total_interests == 2
        assert stats.total_keywords == 4  # kw0, shared, kw1, kw2
        assert stats.avg_relevance_score > 0
        assert len(stats.top_domains) == 3
        assert len(stats.status_breakdown) > 0
        assert len(stats.content_type_breakdown) > 0
        assert len(stats.recent_activity) > 0

    def test_aggregate_caching(self):
        """aggregate() returns cached result on second call within TTL."""
        pages = self._make_pages(2)
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats1 = agg.aggregate(index_instance=index)
        stats2 = agg.aggregate(index_instance=index)

        assert stats1 is stats2

    def test_aggregate_force_refresh(self):
        """aggregate(force_refresh=True) bypasses cache."""
        pages = self._make_pages(2)
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats1 = agg.aggregate(index_instance=index)
        # Modify pages to get different result
        pages2 = self._make_pages(5)
        index.get_all_pages.return_value = pages2
        stats2 = agg.aggregate(index_instance=index, force_refresh=True)

        assert stats1 is not stats2
        assert stats2.total_pages == 5

    def test_aggregate_no_interests_attr(self):
        """aggregate() handles index without interests attribute."""
        pages = self._make_pages(2)
        index = MagicMock(spec=["get_all_pages"])
        index.get_all_pages.return_value = pages

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        assert stats.total_interests == 0


class TestDashboardAggregatorGetPages:
    """Tests for DashboardAggregator._get_pages()."""

    def test_get_pages_via_get_all_pages(self):
        """_get_pages() uses get_all_pages() method when available."""
        pages = [MockPage(url="https://a.com")]
        index = MagicMock()
        index.get_all_pages.return_value = pages

        agg = DashboardAggregator()
        result = agg._get_pages(index)
        assert result == pages
        index.get_all_pages.assert_called_once()

    def test_get_pages_via_pages_attr(self):
        """_get_pages() falls back to pages attribute."""
        pages = [MockPage(url="https://a.com")]
        index = MagicMock(spec=["pages"])
        index.pages = pages

        agg = DashboardAggregator()
        result = agg._get_pages(index)
        assert result == list(pages)

    def test_get_pages_empty(self):
        """_get_pages() returns empty list when no pages source."""
        index = MagicMock(spec=[])

        agg = DashboardAggregator()
        result = agg._get_pages(index)
        assert result == []


class TestDashboardAggregatorComputeTopDomains:
    """Tests for DashboardAggregator._compute_top_domains()."""

    def test_compute_top_domains_basic(self):
        """_compute_top_domains() returns correct domain counts."""
        pages = [
            MockPage(domain="a.com"),
            MockPage(domain="a.com"),
            MockPage(domain="b.com"),
        ]
        agg = DashboardAggregator()
        result = agg._compute_top_domains(pages)

        assert len(result) == 2
        assert result[0]["domain"] == "a.com"
        assert result[0]["count"] == 2
        assert result[1]["domain"] == "b.com"
        assert result[1]["count"] == 1

    def test_compute_top_domains_empty(self):
        """_compute_top_domains() returns empty list for empty pages."""
        agg = DashboardAggregator()
        result = agg._compute_top_domains([])
        assert result == []

    def test_compute_top_domains_limit(self):
        """_compute_top_domains() respects limit parameter."""
        pages = [MockPage(domain=f"domain{i}.com") for i in range(20)]
        agg = DashboardAggregator()
        result = agg._compute_top_domains(pages, limit=5)
        assert len(result) == 5

    def test_compute_top_domains_percentage(self):
        """_compute_top_domains() computes correct percentages."""
        pages = [
            MockPage(domain="a.com"),
            MockPage(domain="a.com"),
            MockPage(domain="b.com"),
        ]
        agg = DashboardAggregator()
        result = agg._compute_top_domains(pages)
        assert result[0]["percentage"] == 66.7  # 2/3 * 100
        assert result[1]["percentage"] == 33.3  # 1/3 * 100

    def test_compute_top_domains_no_domain_attr(self):
        """_compute_top_domains() skips pages without domain."""
        pages = [MockPage(domain="a.com"), MockPage()]
        agg = DashboardAggregator()
        result = agg._compute_top_domains(pages)
        assert len(result) == 1
        assert result[0]["domain"] == "a.com"


class TestDashboardAggregatorComputeStatusBreakdown:
    """Tests for DashboardAggregator._compute_status_breakdown()."""

    def test_compute_status_breakdown_basic(self):
        """_compute_status_breakdown() categorizes status codes correctly."""
        pages = [
            MockPage(status_code=200),
            MockPage(status_code=201),
            MockPage(status_code=404),
            MockPage(status_code=500),
        ]
        agg = DashboardAggregator()
        result = agg._compute_status_breakdown(pages)
        assert result == {"2xx": 2, "4xx": 1, "5xx": 1}

    def test_compute_status_breakdown_empty(self):
        """_compute_status_breakdown() returns empty dict for empty pages."""
        agg = DashboardAggregator()
        result = agg._compute_status_breakdown([])
        assert result == {}

    def test_compute_status_breakdown_zero_status(self):
        """_compute_status_breakdown() handles zero status code as unknown."""
        pages = [MockPage(status_code=0)]
        agg = DashboardAggregator()
        result = agg._compute_status_breakdown(pages)
        assert result == {"unknown": 1}


class TestDashboardAggregatorComputeContentTypes:
    """Tests for DashboardAggregator._compute_content_types()."""

    def test_compute_content_types_basic(self):
        """_compute_content_types() counts content types correctly."""
        pages = [
            MockPage(content_type="text/html"),
            MockPage(content_type="text/html"),
            MockPage(content_type="application/json"),
        ]
        agg = DashboardAggregator()
        result = agg._compute_content_types(pages)
        assert result == {"text/html": 2, "application/json": 1}

    def test_compute_content_types_empty(self):
        """_compute_content_types() returns empty dict for empty pages."""
        agg = DashboardAggregator()
        result = agg._compute_content_types([])
        assert result == {}

    def test_compute_content_types_unknown(self):
        """_compute_content_types() defaults to 'unknown' for empty content_type."""
        pages = [MockPage(content_type="")]
        agg = DashboardAggregator()
        result = agg._compute_content_types(pages)
        assert result == {"unknown": 1}


class TestDashboardAggregatorComputeRecentActivity:
    """Tests for DashboardAggregator._compute_recent_activity()."""

    def test_compute_recent_activity_basic(self):
        """_compute_recent_activity() returns time series points."""
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pages = [
            MockPage(crawled_at=(base + timedelta(days=0)).isoformat()),
            MockPage(crawled_at=(base + timedelta(days=0)).isoformat()),
            MockPage(crawled_at=(base + timedelta(days=1)).isoformat()),
        ]
        agg = DashboardAggregator()
        result = agg._compute_recent_activity(pages)

        assert len(result) == 2
        assert all(isinstance(p, TimeSeriesPoint) for p in result)
        # Most recent day first
        assert result[0].timestamp == "2024-01-02"
        assert result[0].value == 1
        assert result[1].timestamp == "2024-01-01"
        assert result[1].value == 2

    def test_compute_recent_activity_empty(self):
        """_compute_recent_activity() returns empty list for empty pages."""
        agg = DashboardAggregator()
        result = agg._compute_recent_activity([])
        assert result == []

    def test_compute_recent_activity_limit(self):
        """_compute_recent_activity() respects limit parameter."""
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pages = [
            MockPage(crawled_at=(base + timedelta(days=i)).isoformat())
            for i in range(30)
        ]
        agg = DashboardAggregator()
        result = agg._compute_recent_activity(pages, limit=5)
        assert len(result) == 5

    def test_compute_recent_activity_datetime_objects(self):
        """_compute_recent_activity() handles datetime objects (not strings)."""
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pages = [
            MockPage(crawled_at=base),
            MockPage(crawled_at=base + timedelta(days=1)),
        ]
        agg = DashboardAggregator()
        result = agg._compute_recent_activity(pages)
        assert len(result) == 2


class TestDashboardAggregatorClearCache:
    """Tests for DashboardAggregator.clear_cache()."""

    def test_clear_cache(self):
        """clear_cache() resets cached stats and cache time."""
        pages = [MockPage(url="https://a.com")]
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        agg.aggregate(index_instance=index)
        assert agg._cached_stats is not None

        agg.clear_cache()
        assert agg._cached_stats is None
        assert agg._cache_time == 0.0


class TestDashboardAggregatorPagesPerDay:
    """Tests for pages_per_day computation within aggregate()."""

    def test_pages_per_day_computed(self):
        """aggregate() computes pages_per_day when enough pages with dates."""
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pages = [
            MockPage(
                url=f"https://a.com/p{i}",
                domain="a.com",
                crawled_at=(base + timedelta(days=i)).isoformat(),
            )
            for i in range(10)
        ]
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        # 10 pages over 9 days
        assert stats.pages_per_day > 0
        expected = 10 / 9
        assert abs(stats.pages_per_day - expected) < 0.2

    def test_pages_per_day_single_page(self):
        """aggregate() does not compute pages_per_day with only one page."""
        pages = [MockPage(url="https://a.com", crawled_at="2024-01-01T00:00:00")]
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        assert stats.pages_per_day == 0.0


class TestDashboardAggregatorSuccessRate:
    """Tests for crawl_success_rate computation within aggregate()."""

    def test_success_rate_all_success(self):
        """aggregate() computes 100% success rate when all pages are 2xx."""
        pages = [MockPage(status_code=200) for _ in range(5)]
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        assert stats.crawl_success_rate == 100.0

    def test_success_rate_mixed(self):
        """aggregate() computes correct mixed success rate."""
        pages = [
            MockPage(status_code=200),
            MockPage(status_code=200),
            MockPage(status_code=404),
            MockPage(status_code=500),
        ]
        index = MagicMock()
        index.get_all_pages.return_value = pages
        index.interests = []

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        assert stats.crawl_success_rate == 50.0  # 2/4 = 50%

    def test_success_rate_empty_pages(self):
        """aggregate() returns 100% success rate for empty pages."""
        index = MagicMock()
        index.get_all_pages.return_value = []
        index.interests = []

        agg = DashboardAggregator()
        stats = agg.aggregate(index_instance=index)
        assert stats.crawl_success_rate == 100.0
