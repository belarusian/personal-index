"""Adversarial deep tests for personal_index/models.py dataclasses.

Targets: Interest, CrawlConfig, CrawledPage, IndexedPage, SearchResult, Page,
SchedulerConfig, IndexConfig, AppConfig, PipelineStats.

Attack vectors: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, property checks, enum serialization.
"""

import pytest
from datetime import datetime, timezone
from personal_index.models import (
    Interest, InterestType, MatchMode,
    CrawlConfig, CrawledPage, IndexedPage, SearchResult, Page,
    SchedulerConfig, IndexConfig, AppConfig, PipelineStats,
)


# === Interest ===

class TestInterestPriorityClamp:
    def test_priority_below_range_clamped_up(self):
        i = Interest(name="test", priority=0)
        assert i.priority == 1

    def test_priority_above_range_clamped_down(self):
        i = Interest(name="test", priority=15)
        assert i.priority == 10

    def test_priority_negative_clamped_up(self):
        i = Interest(name="test", priority=-5)
        assert i.priority == 1

    def test_priority_huge_clamped_down(self):
        i = Interest(name="test", priority=1000000)
        assert i.priority == 10

    def test_priority_at_bounds_stays(self):
        i1 = Interest(name="test", priority=1)
        i2 = Interest(name="test", priority=10)
        assert i1.priority == 1
        assert i2.priority == 10


class TestInterestKeywordsEdgeCases:
    def test_keywords_as_int_positional(self):
        i = Interest(name="test", keywords=7)
        assert i.priority == 7
        assert i.keywords == []

    def test_keywords_as_string(self):
        i = Interest(name="test", keywords="not a list")
        assert i.keywords == []

    def test_keywords_as_none(self):
        i = Interest(name="test", keywords=None)
        assert i.keywords == []

    def test_empty_keywords_list(self):
        i = Interest(name="test", keywords=[])
        assert i.keywords == []

    def test_duplicate_keywords_preserved(self):
        i = Interest(name="test", keywords=["a", "a", "b"])
        assert i.keywords == ["a", "a", "b"]

    def test_unicode_keywords(self):
        i = Interest(name="test", keywords=["café", "日本語", "🚀"])
        assert i.keywords == ["café", "日本語", "🚀"]

    def test_whitespace_keywords(self):
        i = Interest(name="test", keywords=["  ", ""])
        assert i.keywords == ["  ", ""]


class TestInterestUrlPatternsEdgeCases:
    def test_url_patterns_as_string(self):
        i = Interest(name="test", url_patterns="not a list")
        assert i.url_patterns == []

    def test_url_patterns_as_none(self):
        i = Interest(name="test", url_patterns=None)
        assert i.url_patterns == []

    def test_empty_url_patterns(self):
        i = Interest(name="test", url_patterns=[])
        assert i.url_patterns == []


class TestInterestTopicsEdgeCases:
    def test_topics_as_string(self):
        i = Interest(name="test", topics="not a list")
        assert i.topics == []

    def test_topics_as_none(self):
        i = Interest(name="test", topics=None)
        assert i.topics == []

    def test_empty_topics(self):
        i = Interest(name="test", topics=[])
        assert i.topics == []


class TestInterestRoundTrip:
    def test_to_dict_from_dict_roundtrip(self):
        original = Interest(
            name="test interest",
            interest_type=InterestType.TOPIC,
            value="tech",
            keywords=["python", "ai"],
            url_patterns=["*.example.com"],
            topics=["technology"],
            priority=8,
            enabled=True,
            match_mode=MatchMode.ALL,
        )
        d = original.to_dict()
        restored = Interest.from_dict(d)
        assert restored.name == original.name
        assert restored.interest_type == original.interest_type
        assert restored.value == original.value
        assert restored.keywords == original.keywords
        assert restored.url_patterns == original.url_patterns
        assert restored.topics == original.topics
        assert restored.priority == original.priority
        assert restored.enabled == original.enabled
        assert restored.match_mode == original.match_mode

    def test_to_dict_enum_serialized_to_string(self):
        i = Interest(name="test", interest_type=InterestType.KEYWORD, match_mode=MatchMode.REGEX)
        d = i.to_dict()
        assert d["interest_type"] == "keyword"
        assert d["match_mode"] == "regex"

    def test_from_dict_string_enum_restored(self):
        d = {"name": "test", "interest_type": "topic", "match_mode": "any"}
        i = Interest.from_dict(d)
        assert i.interest_type == InterestType.TOPIC
        assert i.match_mode == MatchMode.ANY

    def test_from_dict_missing_fields_uses_defaults(self):
        d = {"name": "minimal"}
        i = Interest.from_dict(d)
        assert i.name == "minimal"
        assert i.interest_type == InterestType.KEYWORD
        assert i.priority == 5
        assert i.enabled is True

    def test_from_dict_empty_dict_raises_typeerror(self):
        with pytest.raises(TypeError):
            Interest.from_dict({})

    def test_idempotent_roundtrip(self):
        original = Interest(name="test", keywords=["a", "b"], priority=7)
        d1 = original.to_dict()
        restored1 = Interest.from_dict(d1)
        d2 = restored1.to_dict()
        restored2 = Interest.from_dict(d2)
        assert restored1.name == restored2.name
        assert restored1.keywords == restored2.keywords
        assert restored1.priority == restored2.priority


class TestInterestNameEdgeCases:
    def test_empty_name(self):
        i = Interest(name="")
        assert i.name == ""

    def test_whitespace_name(self):
        i = Interest(name="   ")
        assert i.name == "   "

    def test_unicode_name(self):
        i = Interest(name="テスト")
        assert i.name == "テスト"


# === CrawlConfig ===

class TestCrawlConfigEdgeCases:
    def test_defaults(self):
        c = CrawlConfig()
        assert c.max_depth == 3
        assert c.politeness_delay == 1.0
        assert c.rate_limit == 10
        assert c.max_pages_per_domain == 100
        assert c.timeout == 30
        assert c.user_agent == "personal-index/0.1.0"
        assert c.respect_robots_txt is True
        assert c.max_pages == 100
        assert c.max_concurrent_requests == 5
        assert c.request_timeout == 30

    def test_negative_max_depth(self):
        c = CrawlConfig(max_depth=-1)
        assert c.max_depth == -1

    def test_zero_politeness_delay(self):
        c = CrawlConfig(politeness_delay=0)
        assert c.politeness_delay == 0

    def test_huge_rate_limit(self):
        c = CrawlConfig(rate_limit=999999)
        assert c.rate_limit == 999999

    def test_empty_user_agent(self):
        c = CrawlConfig(user_agent="")
        assert c.user_agent == ""

    def test_to_dict_from_dict_roundtrip(self):
        original = CrawlConfig(max_depth=5, politeness_delay=2.0, rate_limit=20)
        d = original.to_dict()
        restored = CrawlConfig.from_dict(d)
        assert restored.max_depth == original.max_depth
        assert restored.politeness_delay == original.politeness_delay
        assert restored.rate_limit == original.rate_limit

    def test_from_dict_ignores_unknown_keys(self):
        d = {"max_depth": 5, "unknown_field": "value"}
        c = CrawlConfig.from_dict(d)
        assert c.max_depth == 5

    def test_blocked_extensions_default_nonempty(self):
        c = CrawlConfig()
        assert len(c.blocked_extensions) > 0
        assert ".jpg" in c.blocked_extensions
        assert ".pdf" in c.blocked_extensions


# === CrawledPage ===

class TestCrawledPageEdgeCases:
    def test_empty_url(self):
        p = CrawledPage(url="")
        assert p.url == ""

    def test_url_with_whitespace(self):
        p = CrawledPage(url="  https://example.com  ")
        assert p.url == "  https://example.com  "

    def test_none_title(self):
        p = CrawledPage(url="https://example.com", title=None)
        assert p.title is None

    def test_empty_title(self):
        p = CrawledPage(url="https://example.com", title="")
        assert p.title == ""

    def test_none_content(self):
        p = CrawledPage(url="https://example.com", content=None)
        assert p.content is None

    def test_unicode_content(self):
        content = "Hello 世界 🌍"
        p = CrawledPage(url="https://example.com", content=content)
        assert p.content == content

    def test_negative_status_code(self):
        p = CrawledPage(url="https://example.com", status_code=-1)
        assert p.status_code == -1

    def test_status_code_above_599(self):
        p = CrawledPage(url="https://example.com", status_code=999)
        assert p.status_code == 999

    def test_negative_depth(self):
        p = CrawledPage(url="https://example.com", depth=-1)
        assert p.depth == -1

    def test_negative_relevance_score(self):
        p = CrawledPage(url="https://example.com", relevance_score=-1.0)
        assert p.relevance_score == -1.0

    def test_relevance_score_above_one(self):
        p = CrawledPage(url="https://example.com", relevance_score=2.0)
        assert p.relevance_score == 2.0

    def test_to_dict_from_dict_roundtrip(self):
        original = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Content",
            status_code=200,
            depth=1,
        )
        d = original.to_dict()
        restored = CrawledPage.from_dict(d)
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.status_code == original.status_code
        assert restored.depth == original.depth

    def test_from_dict_crawled_at_string_parsed(self):
        ts = "2026-01-01T00:00:00+00:00"
        d = {"url": "https://example.com", "crawled_at": ts}
        p = CrawledPage.from_dict(d)
        assert p.crawled_at == datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_from_dict_crawled_at_invalid_string_fallback(self):
        d = {"url": "https://example.com", "crawled_at": "not-a-date"}
        p = CrawledPage.from_dict(d)
        assert isinstance(p.crawled_at, datetime)

    def test_from_dict_crawled_at_missing_fallback(self):
        d = {"url": "https://example.com"}
        p = CrawledPage.from_dict(d)
        assert isinstance(p.crawled_at, datetime)

    def test_from_dict_crawled_at_datetime_kept(self):
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        d = {"url": "https://example.com", "crawled_at": dt}
        p = CrawledPage.from_dict(d)
        assert p.crawled_at == dt

    def test_from_dict_ignores_unknown_keys(self):
        d = {"url": "https://example.com", "unknown": "value"}
        p = CrawledPage.from_dict(d)
        assert p.url == "https://example.com"


# === IndexedPage ===

class TestIndexedPageEdgeCases:
    def test_empty_url(self):
        p = IndexedPage(url="")
        assert p.url == ""

    def test_none_title(self):
        p = IndexedPage(url="https://example.com", title=None)
        assert p.title is None

    def test_none_content(self):
        p = IndexedPage(url="https://example.com", content=None)
        assert p.content is None

    def test_score_property_alias(self):
        p = IndexedPage(url="https://example.com", score=0.75)
        assert p.relevance_score == 0.75
        p.relevance_score = 0.9
        assert p.score == 0.9

    def test_negative_score(self):
        p = IndexedPage(url="https://example.com", score=-1.0)
        assert p.score == -1.0

    def test_score_above_one(self):
        p = IndexedPage(url="https://example.com", score=2.0)
        assert p.score == 2.0

    def test_to_dict_from_dict_roundtrip(self):
        original = IndexedPage(
            url="https://example.com",
            title="Test",
            content="Content",
            score=0.8,
        )
        d = original.to_dict()
        restored = IndexedPage.from_dict(d)
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.score == original.score

    def test_from_dict_ignores_unknown_keys(self):
        d = {"url": "https://example.com", "unknown": "value"}
        p = IndexedPage.from_dict(d)
        assert p.url == "https://example.com"


# === SearchResult ===

class TestSearchResultEdgeCases:
    def test_empty_url(self):
        r = SearchResult(url="")
        assert r.url == ""

    def test_empty_matched_terms(self):
        r = SearchResult(url="https://example.com", matched_terms=[])
        assert r.matched_terms == []

    def test_negative_relevance_score(self):
        r = SearchResult(url="https://example.com", relevance_score=-1.0)
        assert r.relevance_score == -1.0

    def test_relevance_score_above_one(self):
        r = SearchResult(url="https://example.com", relevance_score=2.0)
        assert r.relevance_score == 2.0

    def test_to_dict_from_dict_roundtrip(self):
        original = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="A snippet",
            relevance_score=0.75,
            matched_terms=["term1", "term2"],
        )
        d = original.to_dict()
        restored = SearchResult.from_dict(d)
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.snippet == original.snippet
        assert restored.relevance_score == original.relevance_score
        assert restored.matched_terms == original.matched_terms

    def test_from_dict_ignores_unknown_keys(self):
        d = {"url": "https://example.com", "unknown": "value"}
        r = SearchResult.from_dict(d)
        assert r.url == "https://example.com"


# === Page ===

class TestPageEdgeCases:
    def test_empty_url(self):
        p = Page(url="")
        assert p.url == ""

    def test_none_title(self):
        p = Page(url="https://example.com", title=None)
        assert p.title is None

    def test_none_content(self):
        p = Page(url="https://example.com", content=None)
        assert p.content is None

    def test_id_auto_generated(self):
        p = Page(url="https://example.com")
        assert len(p.id) == 12

    def test_ids_are_unique(self):
        p1 = Page(url="https://example.com/1")
        p2 = Page(url="https://example.com/2")
        assert p1.id != p2.id

    def test_to_dict_from_dict_roundtrip(self):
        original = Page(
            url="https://example.com",
            title="Test",
            content="Content",
        )
        d = original.to_dict()
        restored = Page.from_dict(d)
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.content == original.content

    def test_from_dict_ignores_unknown_keys(self):
        d = {"url": "https://example.com", "unknown": "value"}
        p = Page.from_dict(d)
        assert p.url == "https://example.com"


# === SchedulerConfig ===

class TestSchedulerConfigEdgeCases:
    def test_defaults(self):
        c = SchedulerConfig()
        assert c.enabled is False
        assert c.interval_hours == 24

    def test_negative_interval_hours(self):
        c = SchedulerConfig(interval_hours=-1)
        assert c.interval_hours == -1

    def test_zero_interval_hours(self):
        c = SchedulerConfig(interval_hours=0)
        assert c.interval_hours == 0

    def test_to_dict_from_dict_roundtrip(self):
        original = SchedulerConfig(enabled=True, interval_hours=12)
        d = original.to_dict()
        restored = SchedulerConfig.from_dict(d)
        assert restored.enabled == original.enabled
        assert restored.interval_hours == original.interval_hours

    def test_from_dict_ignores_unknown_keys(self):
        d = {"enabled": True, "unknown": "value"}
        c = SchedulerConfig.from_dict(d)
        assert c.enabled is True


# === IndexConfig ===

class TestIndexConfigEdgeCases:
    def test_defaults(self):
        c = IndexConfig()
        assert c.index_path == ".personal_index"
        assert c.enable_stemming is True

    def test_empty_index_path(self):
        c = IndexConfig(index_path="")
        assert c.index_path == ""

    def test_stemming_disabled(self):
        c = IndexConfig(enable_stemming=False)
        assert c.enable_stemming is False


# === AppConfig ===

class TestAppConfigEdgeCases:
    def test_defaults(self):
        c = AppConfig()
        assert c.data_dir == ".personal_index"
        assert isinstance(c.crawl, CrawlConfig)
        assert isinstance(c.index, IndexConfig)
        assert isinstance(c.scheduler, SchedulerConfig)
        assert c.interests == []

    def test_empty_data_dir(self):
        c = AppConfig(data_dir="")
        assert c.data_dir == ""

    def test_crawler_property_alias(self):
        c = AppConfig()
        assert c.crawler is c.crawl
        new_crawl = CrawlConfig(max_depth=5)
        c.crawler = new_crawl
        assert c.crawl is new_crawl

    def test_to_dict_from_dict_roundtrip(self):
        original = AppConfig(
            interests=[Interest(name="test", priority=7)],
            data_dir="/tmp/test",
        )
        d = original.to_dict()
        restored = AppConfig.from_dict(d)
        assert len(restored.interests) == 1
        assert restored.interests[0].name == "test"
        assert restored.interests[0].priority == 7
        assert restored.data_dir == "/tmp/test"

    def test_from_dict_empty_interests(self):
        d = {"data_dir": "/tmp/test"}
        c = AppConfig.from_dict(d)
        assert c.interests == []

    def test_from_dict_empty_crawl(self):
        d = {"crawl": {}}
        c = AppConfig.from_dict(d)
        assert isinstance(c.crawl, CrawlConfig)


# === PipelineStats ===

class TestPipelineStatsEdgeCases:
    def test_defaults(self):
        s = PipelineStats()
        assert s.pages_crawled == 0
        assert s.pages_extracted == 0
        assert s.pages_passed_filter == 0
        assert s.pages_filtered_out == 0
        assert s.pages_scored == 0
        assert s.pages_tagged == 0
        assert s.pages_indexed == 0
        assert s.tags_applied == 0
        assert s.errors == []
        assert s.elapsed_seconds == 0.0

    def test_negative_counts(self):
        s = PipelineStats(pages_crawled=-1, pages_extracted=-2)
        assert s.pages_crawled == -1
        assert s.pages_extracted == -2

    def test_huge_counts(self):
        s = PipelineStats(pages_crawled=1000000)
        assert s.pages_crawled == 1000000

    def test_summary_format(self):
        s = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_passed_filter=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            pages_indexed=5,
            tags_applied=10,
            errors=["err1", "err2"],
            elapsed_seconds=3.14,
        )
        summary = s.summary()
        parts = summary.split(", ")
        assert len(parts) == 10
        assert parts[0] == "crawled=10"
        assert parts[1] == "extracted=8"
        assert parts[2] == "filtered_in=6"
        assert parts[3] == "filtered_out=2"
        assert parts[4] == "scored=6"
        assert parts[5] == "tagged=5"
        assert parts[6] == "indexed=5"
        assert parts[7] == "tags=10"
        assert parts[8] == "errors=2"
        assert parts[9] == "time=3.1s"

    def test_summary_zero_values(self):
        s = PipelineStats()
        summary = s.summary()
        assert "crawled=0" in summary
        assert "errors=0" in summary
        assert "time=0.0s" in summary

    def test_summary_negative_elapsed(self):
        s = PipelineStats(elapsed_seconds=-1.5)
        summary = s.summary()
        assert "time=-1.5s" in summary

    def test_errors_list_mutability(self):
        s = PipelineStats()
        s.errors.append("error1")
        assert len(s.errors) == 1
        assert s.errors[0] == "error1"
