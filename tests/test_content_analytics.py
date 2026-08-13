"""Tests for content_analytics module."""

import pytest

from personal_index.content_analytics import ContentAnalytics


@pytest.fixture
def analytics():
    a = ContentAnalytics()
    a.add_items([
        {"id": "1", "title": "Short", "description": "A", "tags": ["a", "b"], "link": "http://x.com"},
        {"id": "2", "title": "Medium Title", "description": "AB", "tags": ["a", "c"]},
        {"id": "3", "title": "Very Long Title Here", "description": "ABC", "tags": ["b"]},
    ])
    return a


class TestBasicStats:
    def test_total_items(self, analytics):
        assert analytics.total_items == 3

    def test_clear(self, analytics):
        analytics.clear()
        assert analytics.total_items == 0


class TestTagAnalytics:
    def test_tag_counts(self, analytics):
        counts = analytics.get_tag_counts()
        assert counts["a"] == 2
        assert counts["b"] == 2
        assert counts["c"] == 1

    def test_unique_tags_count(self, analytics):
        assert analytics.get_unique_tags_count() == 3

    def test_items_by_tag(self, analytics):
        items = analytics.get_items_by_tag("a")
        assert len(items) == 2

    def test_items_by_tag_none(self, analytics):
        items = analytics.get_items_by_tag("nonexistent")
        assert items == []


class TestTitleLength:
    def test_title_lengths(self, analytics):
        lengths = analytics.get_title_lengths()
        assert lengths == [5, 12, 20]

    def test_avg_title_length(self, analytics):
        avg = analytics.get_avg_title_length()
        assert abs(avg - (5 + 14 + 18) / 3) < 0.01


class TestDescriptionLength:
    def test_description_lengths(self, analytics):
        lengths = analytics.get_description_lengths()
        assert lengths == [1, 2, 3]

    def test_avg_description_length(self, analytics):
        avg = analytics.get_avg_description_length()
        assert abs(avg - (1 + 2 + 3) / 3) < 0.01


class TestLinkAnalytics:
    def test_items_with_links(self, analytics):
        items = analytics.get_items_with_links()
        assert len(items) == 1

    def test_link_ratio(self, analytics):
        ratio = analytics.get_link_ratio()
        assert abs(ratio - 1/3) < 0.01


class TestTagDistribution:
    def test_tag_distribution(self, analytics):
        dist = analytics.get_tag_distribution()
        # Total tags: a=2, b=2, c=1 => 5 total
        assert abs(dist["a"] - 40) < 0.01  # 2/5 = 40%
        assert abs(dist["b"] - 40) < 0.01
        assert abs(dist["c"] - 20) < 0.01

    def test_tag_distribution_empty(self):
        analytics = ContentAnalytics()
        dist = analytics.get_tag_distribution()
        assert dist == {}

    def test_empty_title_lengths(self):
        a = ContentAnalytics()
        assert a.get_title_lengths() == []

    def test_empty_avg_title_length(self):
        a = ContentAnalytics()
        assert a.get_avg_title_length() == 0.0

    def test_empty_description_lengths(self):
        a = ContentAnalytics()
        assert a.get_description_lengths() == []

    def test_empty_avg_description_length(self):
        a = ContentAnalytics()
        assert a.get_avg_description_length() == 0.0

    def test_empty_link_ratio(self):
        a = ContentAnalytics()
        assert a.get_link_ratio() == 0.0

    def test_empty_items_with_links(self):
        a = ContentAnalytics()
        assert a.get_items_with_links() == []

    def test_empty_tag_counts(self):
        a = ContentAnalytics()
        assert a.get_tag_counts() == {}

    def test_empty_unique_tags(self):
        a = ContentAnalytics()
        assert a.get_unique_tags_count() == 0

    def test_items_no_tags(self):
        a = ContentAnalytics()
        a.add_items([{"id": "1", "title": "No tags"}])
        assert a.get_tag_counts() == {}

    def test_items_with_none_tags(self):
        a = ContentAnalytics()
        a.add_items([{"id": "1", "title": "None tags", "tags": None}])
        assert a.get_tag_counts() == {}

    def test_add_items_multiple_batches(self):
        a = ContentAnalytics()
        a.add_items([{"id": "1"}])
        a.add_items([{"id": "2"}, {"id": "3"}])
        assert a.total_items == 3

    def test_link_ratio_all_linked(self):
        a = ContentAnalytics()
        a.add_items([
            {"id": "1", "link": "http://a.com"},
            {"id": "2", "link": "http://b.com"},
        ])
        assert a.get_link_ratio() == 1.0
