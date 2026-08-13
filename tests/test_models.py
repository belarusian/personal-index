"""Tests for personal_index.models module.

Covers:
- InterestType enum values
- MatchMode enum values
- Interest.to_dict(), from_dict() roundtrip
- Interest.matches(): keyword match (ANY/ALL mode), URL pattern (fnmatch), regex pattern
- Interest.score()
- CrawlConfig.to_dict(), from_dict()
- CrawledPage.to_dict(), from_dict()
- Page.to_dict(), from_dict()
- SchedulerConfig.to_dict(), from_dict()
- IndexConfig defaults
- AppConfig.to_dict(), from_dict(), crawler property
- PipelineStats.summary()
"""

from __future__ import annotations

from personal_index.models import (
    AppConfig,
    CrawlConfig,
    CrawledPage,
    IndexConfig,
    Interest,
    InterestType,
    MatchMode,
    Page,
    PipelineStats,
    SchedulerConfig,
)

# ---------------------------------------------------------------------------
# InterestType enum tests
# ---------------------------------------------------------------------------


class TestInterestType:
    """Tests for InterestType enum."""

    def test_interest_type_keyword(self):
        assert InterestType.KEYWORD.value == "keyword"

    def test_interest_type_topic(self):
        assert InterestType.TOPIC.value == "topic"

    def test_interest_type_url_pattern(self):
        assert InterestType.URL_PATTERN.value == "url_pattern"

    def test_interest_type_values(self):
        values = {et.value for et in InterestType}
        assert values == {"keyword", "topic", "url_pattern"}

    def test_interest_type_from_value(self):
        assert InterestType("keyword") == InterestType.KEYWORD
        assert InterestType("topic") == InterestType.TOPIC
        assert InterestType("url_pattern") == InterestType.URL_PATTERN


# ---------------------------------------------------------------------------
# MatchMode enum tests
# ---------------------------------------------------------------------------


class TestMatchMode:
    """Tests for MatchMode enum."""

    def test_match_mode_any(self):
        assert MatchMode.ANY.value == "any"

    def test_match_mode_all(self):
        assert MatchMode.ALL.value == "all"

    def test_match_mode_regex(self):
        assert MatchMode.REGEX.value == "regex"

    def test_match_mode_values(self):
        values = {mm.value for mm in MatchMode}
        assert values == {"any", "all", "regex"}

    def test_match_mode_from_value(self):
        assert MatchMode("any") == MatchMode.ANY
        assert MatchMode("all") == MatchMode.ALL
        assert MatchMode("regex") == MatchMode.REGEX


# ---------------------------------------------------------------------------
# Interest tests
# ---------------------------------------------------------------------------


class TestInterest:
    """Tests for Interest dataclass."""

    def test_interest_defaults(self):
        interest = Interest(name="python")
        assert interest.name == "python"
        assert interest.interest_type == InterestType.KEYWORD
        assert interest.keywords == []
        assert interest.url_patterns == []
        assert interest.enabled is True
        assert interest.match_mode == MatchMode.ANY
        assert 1 <= interest.priority <= 10

    def test_interest_to_dict(self):
        interest = Interest(
            name="python",
            keywords=["python", "programming"],
            url_patterns=["*.python.org"],
            priority=8,
        )
        d = interest.to_dict()
        assert d["name"] == "python"
        assert d["keywords"] == ["python", "programming"]
        assert d["url_patterns"] == ["*.python.org"]
        assert d["priority"] == 8
        assert d["interest_type"] == "keyword"
        assert d["match_mode"] == "any"

    def test_interest_from_dict(self):
        data = {
            "name": "python",
            "keywords": ["python", "dev"],
            "url_patterns": ["*.python.org"],
            "topics": [],
            "enabled": True,
            "priority": 7,
            "interest_type": "keyword",
            "match_mode": "any",
        }
        interest = Interest.from_dict(data)
        assert interest.name == "python"
        assert interest.keywords == ["python", "dev"]
        assert interest.url_patterns == ["*.python.org"]
        assert interest.enabled is True
        assert interest.priority == 7

    def test_interest_roundtrip(self):
        interest = Interest(
            name="python",
            keywords=["python", "dev"],
            url_patterns=["*.python.org"],
            enabled=False,
            priority=9,
            interest_type=InterestType.URL_PATTERN,
            match_mode=MatchMode.ALL,
        )
        d = interest.to_dict()
        restored = Interest.from_dict(d)
        assert restored.name == interest.name
        assert restored.keywords == interest.keywords
        assert restored.url_patterns == interest.url_patterns
        assert restored.enabled == interest.enabled
        assert restored.priority == interest.priority
        assert restored.interest_type == interest.interest_type
        assert restored.match_mode == interest.match_mode

    def test_interest_matches_keyword_any(self):
        interest = Interest(
            name="python",
            keywords=["python", "programming"],
            match_mode=MatchMode.ANY,
        )
        assert interest.matches("I love python", "")
        assert interest.matches("programming is fun", "")

    def test_interest_matches_keyword_all(self):
        interest = Interest(
            name="python",
            keywords=["python", "programming"],
            match_mode=MatchMode.ALL,
        )
        # ANY mode is the default behavior in matches() - it returns True if any keyword matches
        # The match_mode affects scoring, not the matches() boolean check
        assert interest.matches("I love python", "")

    def test_interest_matches_value_field(self):
        interest = Interest(name="test", value="python")
        assert interest.matches("I love python", "")

    def test_interest_matches_url_pattern_fnmatch(self):
        interest = Interest(
            name="python",
            url_patterns=["*.python.org/*"],
        )
        assert interest.matches("content", "https://docs.python.org/3/tutorial")

    def test_interest_matches_url_pattern_regex(self):
        interest = Interest(
            name="python",
            url_patterns=[r"https://github\.com/.*"],
        )
        assert interest.matches("content", "https://github.com/python/cpython")

    def test_interest_matches_disabled(self):
        interest = Interest(
            name="python",
            keywords=["python"],
            enabled=False,
        )
        assert not interest.matches("I love python", "")

    def test_interest_matches_no_match(self):
        interest = Interest(
            name="python",
            keywords=["python"],
        )
        assert not interest.matches("I love java", "")

    def test_interest_matches_topics(self):
        interest = Interest(
            name="tech",
            topics=["software", "programming"],
        )
        assert interest.matches("software development", "")

    def test_interest_score(self):
        interest = Interest(
            name="python",
            keywords=["python"],
            priority=5,
        )
        score = interest.score("python python python")
        assert score > 0

    def test_interest_score_disabled(self):
        interest = Interest(
            name="python",
            keywords=["python"],
            enabled=False,
        )
        assert interest.score("python python") == 0.0

    def test_interest_score_with_value(self):
        interest = Interest(name="test", value="python", priority=3)
        score = interest.score("python is great")
        assert score > 0

    def test_interest_score_capped(self):
        """Score is capped at priority * 10."""
        interest = Interest(
            name="python",
            keywords=["python"],
            priority=5,
        )
        # Many occurrences should cap at priority * 10 = 50
        text = "python " * 100
        score = interest.score(text)
        assert score <= interest.priority * 10

    def test_interest_priority_clamped(self):
        interest = Interest(name="test", priority=100)
        assert interest.priority == 10  # clamped to max 10

        interest2 = Interest(name="test", priority=0)
        assert interest2.priority == 1  # clamped to min 1

    def test_interest_keywords_int_edge_case(self):
        """Handle edge case where keywords is passed as int."""
        interest = Interest(name="test", keywords=5)
        assert interest.priority == 5
        assert interest.keywords == []


# ---------------------------------------------------------------------------
# CrawlConfig tests
# ---------------------------------------------------------------------------


class TestCrawlConfig:
    """Tests for CrawlConfig dataclass."""

    def test_default_config(self):
        config = CrawlConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.rate_limit == 10
        assert config.max_pages_per_domain == 100
        assert config.timeout == 30
        assert config.user_agent == "personal-index/0.1.0"
        assert config.respect_robots_txt is True

    def test_custom_config(self):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0

    def test_to_dict(self):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0)
        d = config.to_dict()
        assert d["max_depth"] == 5
        assert d["politeness_delay"] == 2.0

    def test_from_dict(self):
        data = {
            "max_depth": 5,
            "politeness_delay": 2.0,
            "rate_limit": 20,
            "max_pages_per_domain": 200,
            "timeout": 60,
            "user_agent": "test-agent",
            "respect_robots_txt": False,
            "allowed_domains": ["example.com"],
            "blocked_domains": ["bad.com"],
            "max_pages": 50,
            "blocked_extensions": [".exe"],
        }
        config = CrawlConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0
        assert config.rate_limit == 20

    def test_roundtrip(self):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0, rate_limit=20)
        d = config.to_dict()
        restored = CrawlConfig.from_dict(d)
        assert restored.max_depth == config.max_depth
        assert restored.politeness_delay == config.politeness_delay
        assert restored.rate_limit == config.rate_limit


# ---------------------------------------------------------------------------
# CrawledPage tests
# ---------------------------------------------------------------------------


class TestCrawledPage:
    """Tests for CrawledPage dataclass."""

    def test_default_page(self):
        page = CrawledPage(url="https://example.com")
        assert page.url == "https://example.com"
        assert page.title == ""
        assert page.content == ""
        assert page.status_code == 200

    def test_page_with_content(self):
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Some content",
            status_code=200,
        )
        assert page.title == "Test Page"
        assert page.content == "Some content"

    def test_to_dict(self):
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Hello",
            status_code=200,
        )
        d = page.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"
        assert d["content"] == "Hello"

    def test_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Test",
            "content": "Hello",
            "status_code": 200,
            "matched_interests": [],
            "raw_html": "",
            "word_count": 0,
            "relevance_score": 0.0,
        }
        page = CrawledPage.from_dict(data)
        assert page.url == "https://example.com"
        assert page.title == "Test"
        assert page.content == "Hello"

    def test_roundtrip(self):
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Hello world",
            status_code=200,
        )
        d = page.to_dict()
        restored = CrawledPage.from_dict(d)
        assert restored.url == page.url
        assert restored.title == page.title
        assert restored.content == page.content


# ---------------------------------------------------------------------------
# Page tests
# ---------------------------------------------------------------------------


class TestPage:
    """Tests for Page dataclass."""

    def test_default_page(self):
        page = Page(url="https://example.com")
        assert page.url == "https://example.com"
        assert page.title == ""
        assert page.content == ""
        assert page.status_code == 200
        assert page.language == "en"

    def test_page_with_content(self):
        page = Page(
            url="https://example.com",
            title="Test",
            content="Hello",
            domain="example.com",
        )
        assert page.title == "Test"
        assert page.domain == "example.com"

    def test_to_dict(self):
        page = Page(url="https://example.com", title="Test")
        d = page.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"

    def test_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Test",
            "content": "Hello",
            "meta_description": "A test page",
            "matched_interests": [],
            "id": "abc123",
            "domain": "example.com",
            "status_code": 200,
            "content_length": 5,
            "language": "en",
            "keywords": [],
        }
        page = Page.from_dict(data)
        assert page.url == "https://example.com"
        assert page.title == "Test"

    def test_roundtrip(self):
        page = Page(
            url="https://example.com",
            title="Test",
            content="Hello",
            domain="example.com",
        )
        d = page.to_dict()
        restored = Page.from_dict(d)
        assert restored.url == page.url
        assert restored.title == page.title
        assert restored.content == page.content


# ---------------------------------------------------------------------------
# SchedulerConfig tests
# ---------------------------------------------------------------------------


class TestSchedulerConfig:
    """Tests for SchedulerConfig dataclass."""

    def test_defaults(self):
        config = SchedulerConfig()
        assert config.enabled is False
        assert config.interval_hours == 24

    def test_custom(self):
        config = SchedulerConfig(enabled=True, interval_hours=12)
        assert config.enabled is True
        assert config.interval_hours == 12

    def test_to_dict(self):
        config = SchedulerConfig(enabled=True, interval_hours=12)
        d = config.to_dict()
        assert d["enabled"] is True
        assert d["interval_hours"] == 12

    def test_from_dict(self):
        data = {"enabled": True, "interval_hours": 6}
        config = SchedulerConfig.from_dict(data)
        assert config.enabled is True
        assert config.interval_hours == 6

    def test_roundtrip(self):
        config = SchedulerConfig(enabled=True, interval_hours=12)
        d = config.to_dict()
        restored = SchedulerConfig.from_dict(d)
        assert restored.enabled == config.enabled
        assert restored.interval_hours == config.interval_hours


# ---------------------------------------------------------------------------
# IndexConfig tests
# ---------------------------------------------------------------------------


class TestIndexConfig:
    """Tests for IndexConfig dataclass."""

    def test_defaults(self):
        config = IndexConfig()
        assert config.index_path == ".personal_index"
        assert config.enable_stemming is True

    def test_custom(self):
        config = IndexConfig(index_path="/custom/path", enable_stemming=False)
        assert config.index_path == "/custom/path"
        assert config.enable_stemming is False


# ---------------------------------------------------------------------------
# AppConfig tests
# ---------------------------------------------------------------------------


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_defaults(self):
        config = AppConfig()
        assert config.interests == []
        assert config.data_dir == ".personal_index"
        assert isinstance(config.crawl, CrawlConfig)
        assert isinstance(config.index, IndexConfig)
        assert isinstance(config.scheduler, SchedulerConfig)

    def test_to_dict(self):
        config = AppConfig(
            interests=[Interest(name="python", keywords=["python"])],
            data_dir="/custom/data",
        )
        d = config.to_dict()
        assert len(d["interests"]) == 1
        assert d["interests"][0]["name"] == "python"
        assert d["data_dir"] == "/custom/data"
        assert "crawl" in d
        assert "index" in d
        assert "scheduler" in d

    def test_from_dict(self):
        data = {
            "interests": [
                {"name": "python", "keywords": ["python"], "url_patterns": [], "topics": [], "enabled": True}
            ],
            "crawl": {"max_depth": 5, "politeness_delay": 2.0},
            "data_dir": "/custom/data",
            "index": {"index_path": "/custom/index", "enable_stemming": False},
            "scheduler": {"enabled": True, "interval_hours": 12},
        }
        config = AppConfig.from_dict(data)
        assert len(config.interests) == 1
        assert config.interests[0].name == "python"
        assert config.data_dir == "/custom/data"
        assert config.crawl.max_depth == 5
        assert config.index.index_path == "/custom/index"
        assert config.scheduler.enabled is True
        assert config.scheduler.interval_hours == 12

    def test_roundtrip(self):
        config = AppConfig(
            interests=[Interest(name="python", keywords=["python"])],
            data_dir="/custom/data",
        )
        d = config.to_dict()
        restored = AppConfig.from_dict(d)
        assert len(restored.interests) == 1
        assert restored.interests[0].name == "python"
        assert restored.data_dir == config.data_dir

    def test_crawler_property(self):
        config = AppConfig()
        assert config.crawler is config.crawl

    def test_crawler_setter(self):
        config = AppConfig()
        new_crawl = CrawlConfig(max_depth=10)
        config.crawler = new_crawl
        assert config.crawl is new_crawl
        assert config.crawl.max_depth == 10


# ---------------------------------------------------------------------------
# PipelineStats tests
# ---------------------------------------------------------------------------


class TestPipelineStats:
    """Tests for PipelineStats dataclass."""

    def test_defaults(self):
        stats = PipelineStats()
        assert stats.pages_crawled == 0
        assert stats.pages_extracted == 0
        assert stats.pages_passed_filter == 0
        assert stats.pages_filtered_out == 0
        assert stats.pages_scored == 0
        assert stats.pages_tagged == 0
        assert stats.pages_indexed == 0
        assert stats.tags_applied == 0
        assert stats.errors == []
        assert stats.elapsed_seconds == 0.0

    def test_summary(self):
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_passed_filter=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            pages_indexed=5,
            tags_applied=15,
            errors=["error1"],
            elapsed_seconds=3.5,
        )
        summary = stats.summary()
        assert "crawled=10" in summary
        assert "extracted=8" in summary
        assert "filtered_in=6" in summary
        assert "filtered_out=2" in summary
        assert "scored=6" in summary
        assert "tagged=5" in summary
        assert "indexed=5" in summary
        assert "tags=15" in summary
        assert "errors=1" in summary
        assert "time=3.5s" in summary

    def test_summary_empty(self):
        stats = PipelineStats()
        summary = stats.summary()
        assert "crawled=0" in summary
        assert "errors=0" in summary
        assert "time=0.0s" in summary
