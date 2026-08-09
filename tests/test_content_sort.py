"""Tests for content sort - sorting saved items."""

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_sort import (
    SortField,
    SortDirection,
    SortConfig,
    ContentSorter,
    SortResult,
)


class TestSortField:
    def test_title_field(self):
        assert SortField.TITLE.value == "title"

    def test_score_field(self):
        assert SortField.SCORE.value == "score"

    def test_date_field(self):
        assert SortField.DATE.value == "date"

    def test_domain_field(self):
        assert SortField.DOMAIN.value == "domain"

    def test_content_type_field(self):
        assert SortField.CONTENT_TYPE.value == "content_type"

    def test_tags_field(self):
        assert SortField.TAGS.value == "tags"

    def test_status_field(self):
        assert SortField.STATUS.value == "status"

    def test_length_field(self):
        assert SortField.LENGTH.value == "length"

    def test_relevance_field(self):
        assert SortField.RELEVANCE.value == "relevance"

    def test_all_fields_defined(self):
        values = [f.value for f in SortField]
        assert "title" in values
        assert "score" in values
        assert "date" in values
        assert "domain" in values
        assert "content_type" in values
        assert "tags" in values
        assert "status" in values
        assert "length" in values
        assert "relevance" in values


class TestSortDirection:
    def test_ascending(self):
        assert SortDirection.ASC.value == "asc"

    def test_descending(self):
        assert SortDirection.DESC.value == "desc"

    def test_from_string_asc(self):
        d = SortDirection.from_string("asc")
        assert d == SortDirection.ASC

    def test_from_string_desc(self):
        d = SortDirection.from_string("desc")
        assert d == SortDirection.DESC

    def test_from_string_invalid(self):
        d = SortDirection.from_string("invalid")
        assert d == SortDirection.DESC

    def test_from_string_empty(self):
        d = SortDirection.from_string("")
        assert d == SortDirection.DESC


class TestSortConfig:
    def test_default_config(self):
        config = SortConfig()
        assert config.sort_field == SortField.SCORE
        assert config.direction == SortDirection.DESC

    def test_custom_config(self):
        config = SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC)
        assert config.sort_field == SortField.TITLE
        assert config.direction == SortDirection.ASC

    def test_multiple_sort_keys(self):
        keys = [
            SortConfig(sort_field=SortField.SCORE, direction=SortDirection.DESC),
            SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC),
        ]
        config = SortConfig(sort_keys=keys)
        assert len(config.sort_keys) == 2

    def test_config_to_dict(self):
        config = SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC)
        d = config.to_dict()
        assert d["field"] == "title"
        assert d["direction"] == "asc"

    def test_config_from_dict(self):
        d = {"field": "title", "direction": "asc"}
        config = SortConfig.from_dict(d)
        assert config.sort_field == SortField.TITLE
        assert config.direction == SortDirection.ASC

    def test_config_from_dict_with_sort_keys(self):
        d = {
            "sort_keys": [
                {"field": "score", "direction": "desc"},
                {"field": "title", "direction": "asc"},
            ]
        }
        config = SortConfig.from_dict(d)
        assert len(config.sort_keys) == 2
        assert config.sort_keys[0].sort_field == SortField.SCORE


class TestSortResult:
    def test_default_result(self):
        result = SortResult()
        assert result.items == []
        assert result.sort_field is None
        assert result.sort_direction is None

    def test_result_with_data(self):
        result = SortResult(
            items=["a", "b"],
            sort_field=SortField.TITLE,
            sort_direction=SortDirection.ASC,
        )
        assert len(result.items) == 2
        assert result.sort_field == SortField.TITLE
        assert result.sort_direction == SortDirection.ASC

    def test_result_to_dict(self):
        result = SortResult(items=["x"], sort_field=SortField.SCORE, sort_direction=SortDirection.DESC)
        d = result.to_dict()
        assert d["sort_field"] == "score"
        assert d["sort_direction"] == "desc"


class TestContentSorterSortByTitle:
    def test_sort_by_title_asc(self):
        items = [
            {"title": "Zebra"},
            {"title": "Apple"},
            {"title": "Mango"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE, direction=SortDirection.ASC)
        assert result[0]["title"] == "Apple"
        assert result[1]["title"] == "Mango"
        assert result[2]["title"] == "Zebra"

    def test_sort_by_title_desc(self):
        items = [
            {"title": "Zebra"},
            {"title": "Apple"},
            {"title": "Mango"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE, direction=SortDirection.DESC)
        assert result[0]["title"] == "Zebra"
        assert result[2]["title"] == "Apple"

    def test_sort_by_title_case_insensitive(self):
        items = [
            {"title": "zebra"},
            {"title": "Apple"},
            {"title": "mango"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE, direction=SortDirection.ASC)
        assert result[0]["title"] == "Apple"

    def test_sort_by_title_empty_titles(self):
        items = [
            {"title": ""},
            {"title": "Apple"},
            {"title": ""},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE, direction=SortDirection.ASC)
        assert result[0]["title"] == ""


class TestContentSorterSortByScore:
    def test_sort_by_score_desc(self):
        items = [
            {"score": 3.0},
            {"score": 9.0},
            {"score": 5.0},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.SCORE, direction=SortDirection.DESC)
        assert result[0]["score"] == 9.0
        assert result[1]["score"] == 5.0
        assert result[2]["score"] == 3.0

    def test_sort_by_score_asc(self):
        items = [
            {"score": 3.0},
            {"score": 9.0},
            {"score": 5.0},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.SCORE, direction=SortDirection.ASC)
        assert result[0]["score"] == 3.0
        assert result[2]["score"] == 9.0

    def test_sort_by_score_missing(self):
        items = [
            {"score": 3.0},
            {"title": "no score"},
            {"score": 9.0},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.SCORE, direction=SortDirection.DESC)
        assert result[0]["score"] == 9.0


class TestContentSorterSortByDate:
    def test_sort_by_date_desc(self):
        now = datetime.now(timezone.utc)
        items = [
            {"date": (now - timedelta(days=10)).isoformat()},
            {"date": now.isoformat()},
            {"date": (now - timedelta(days=5)).isoformat()},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.DATE, direction=SortDirection.DESC)
        assert result[0]["date"] == now.isoformat()
        assert result[2]["date"] == (now - timedelta(days=10)).isoformat()

    def test_sort_by_date_asc(self):
        now = datetime.now(timezone.utc)
        items = [
            {"date": (now - timedelta(days=10)).isoformat()},
            {"date": now.isoformat()},
            {"date": (now - timedelta(days=5)).isoformat()},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.DATE, direction=SortDirection.ASC)
        assert result[0]["date"] == (now - timedelta(days=10)).isoformat()
        assert result[2]["date"] == now.isoformat()

    def test_sort_by_date_missing(self):
        items = [
            {"date": "2024-01-01T00:00:00+00:00"},
            {"title": "no date"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.DATE, direction=SortDirection.DESC)
        assert result[0]["date"] == "2024-01-01T00:00:00+00:00"


class TestContentSorterSortByDomain:
    def test_sort_by_domain_asc(self):
        items = [
            {"domain": "z-site.com"},
            {"domain": "a-site.com"},
            {"domain": "m-site.com"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.DOMAIN, direction=SortDirection.ASC)
        assert result[0]["domain"] == "a-site.com"
        assert result[2]["domain"] == "z-site.com"

    def test_sort_by_domain_desc(self):
        items = [
            {"domain": "z-site.com"},
            {"domain": "a-site.com"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.DOMAIN, direction=SortDirection.DESC)
        assert result[0]["domain"] == "z-site.com"


class TestContentSorterSortByContentType:
    def test_sort_by_content_type(self):
        items = [
            {"content_type": "video"},
            {"content_type": "article"},
            {"content_type": "image"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.CONTENT_TYPE, direction=SortDirection.ASC)
        assert result[0]["content_type"] == "article"
        assert result[1]["content_type"] == "image"
        assert result[2]["content_type"] == "video"


class TestContentSorterSortByTags:
    def test_sort_by_tags_count_desc(self):
        items = [
            {"tags": ["a", "b", "c"]},
            {"tags": ["a"]},
            {"tags": ["a", "b"]},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TAGS, direction=SortDirection.DESC)
        assert len(result[0]["tags"]) == 3
        assert len(result[2]["tags"]) == 1

    def test_sort_by_tags_count_asc(self):
        items = [
            {"tags": ["a", "b", "c"]},
            {"tags": ["a"]},
            {"tags": ["a", "b"]},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TAGS, direction=SortDirection.ASC)
        assert len(result[0]["tags"]) == 1
        assert len(result[2]["tags"]) == 3


class TestContentSorterSortByStatus:
    def test_sort_by_status(self):
        items = [
            {"status": "archived"},
            {"status": "active"},
            {"status": "draft"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.STATUS, direction=SortDirection.ASC)
        assert result[0]["status"] == "active"
        assert result[1]["status"] == "archived"
        assert result[2]["status"] == "draft"


class TestContentSorterSortByLength:
    def test_sort_by_length_desc(self):
        items = [
            {"content": "short"},
            {"content": "this is a much longer piece of content"},
            {"content": "medium length text here"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.LENGTH, direction=SortDirection.DESC)
        assert result[0]["content"] == "this is a much longer piece of content"

    def test_sort_by_length_asc(self):
        items = [
            {"content": "short"},
            {"content": "this is a much longer piece of content"},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.LENGTH, direction=SortDirection.ASC)
        assert result[0]["content"] == "short"


class TestContentSorterSortByRelevance:
    def test_sort_by_relevance_desc(self):
        items = [
            {"relevance": 0.3},
            {"relevance": 0.9},
            {"relevance": 0.5},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.RELEVANCE, direction=SortDirection.DESC)
        assert result[0]["relevance"] == 0.9
        assert result[2]["relevance"] == 0.3


class TestContentSorterMultiSort:
    def test_multi_sort_primary_then_secondary(self):
        items = [
            {"score": 5.0, "title": "B"},
            {"score": 5.0, "title": "A"},
            {"score": 8.0, "title": "C"},
        ]
        sorter = ContentSorter()
        keys = [
            SortConfig(sort_field=SortField.SCORE, direction=SortDirection.DESC),
            SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC),
        ]
        result = sorter.sort_multi(items, sort_keys=keys)
        assert result[0]["score"] == 8.0
        assert result[1]["title"] == "A"
        assert result[2]["title"] == "B"

    def test_multi_sort_three_keys(self):
        items = [
            {"score": 5.0, "title": "B", "date": "2024-01-02"},
            {"score": 5.0, "title": "A", "date": "2024-01-01"},
            {"score": 5.0, "title": "A", "date": "2024-01-03"},
        ]
        sorter = ContentSorter()
        keys = [
            SortConfig(sort_field=SortField.SCORE, direction=SortDirection.DESC),
            SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC),
            SortConfig(sort_field=SortField.DATE, direction=SortDirection.DESC),
        ]
        result = sorter.sort_multi(items, sort_keys=keys)
        assert result[0]["date"] == "2024-01-03"
        assert result[1]["date"] == "2024-01-01"
        assert result[2]["title"] == "B"


class TestContentSorterEdgeCases:
    def test_sort_empty_items(self):
        sorter = ContentSorter()
        result = sorter.sort([], sort_field=SortField.TITLE)
        assert result == []

    def test_sort_single_item(self):
        items = [{"title": "only"}]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE)
        assert len(result) == 1

    def test_sort_stable_order(self):
        items = [
            {"title": "A", "score": 5.0},
            {"title": "B", "score": 5.0},
            {"title": "C", "score": 5.0},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.SCORE, direction=SortDirection.DESC)
        assert result[0]["title"] == "A"
        assert result[1]["title"] == "B"
        assert result[2]["title"] == "C"

    def test_sort_with_none_values(self):
        items = [
            {"title": None},
            {"title": "Apple"},
            {"title": None},
        ]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE, direction=SortDirection.ASC)
        assert result[0]["title"] is None

    def test_sort_preserves_items(self):
        items = [{"title": "test", "extra": "data"}]
        sorter = ContentSorter()
        result = sorter.sort(items, sort_field=SortField.TITLE)
        assert result[0]["extra"] == "data"

    def test_sort_with_config(self):
        items = [
            {"title": "Z"},
            {"title": "A"},
        ]
        sorter = ContentSorter()
        config = SortConfig(sort_field=SortField.TITLE, direction=SortDirection.ASC)
        result = sorter.sort_with_config(items, config)
        assert result[0]["title"] == "A"
