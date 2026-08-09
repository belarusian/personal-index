"""Tests for content search filters - advanced search filtering capabilities."""

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_search_filters import (
    SearchFilter,
    FilterCondition,
    FilterOperator,
    FilterGroup,
    FilterResult,
    DateRangeFilter,
    ScoreFilter,
    ContentTypeFilter,
    TagFilter,
    DomainFilter,
    StatusFilter,
    CombinedFilter,
)


class TestFilterOperator:
    def test_equality_operator(self):
        op = FilterOperator.EQUALS
        assert op.value == "eq"

    def test_contains_operator(self):
        op = FilterOperator.CONTAINS
        assert op.value == "contains"

    def test_greater_than_operator(self):
        op = FilterOperator.GREATER_THAN
        assert op.value == "gt"

    def test_less_than_operator(self):
        op = FilterOperator.LESS_THAN
        assert op.value == "lt"

    def test_in_operator(self):
        op = FilterOperator.IN
        assert op.value == "in"

    def test_starts_with_operator(self):
        op = FilterOperator.STARTS_WITH
        assert op.value == "starts_with"

    def test_regex_operator(self):
        op = FilterOperator.REGEX
        assert op.value == "regex"

    def test_all_operators_defined(self):
        ops = [o.value for o in FilterOperator]
        assert "eq" in ops
        assert "contains" in ops
        assert "gt" in ops
        assert "lt" in ops
        assert "in" in ops


class TestFilterCondition:
    def test_basic_condition(self):
        cond = FilterCondition(field="title", operator=FilterOperator.EQUALS, value="Python")
        assert cond.field == "title"
        assert cond.operator == FilterOperator.EQUALS
        assert cond.value == "Python"

    def test_condition_with_negation(self):
        cond = FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value="rust", negate=True)
        assert cond.negate is True

    def test_condition_to_dict(self):
        cond = FilterCondition(field="score", operator=FilterOperator.GREATER_THAN, value=5.0)
        d = cond.to_dict()
        assert d["field"] == "score"
        assert d["operator"] == "gt"
        assert d["value"] == 5.0

    def test_condition_from_dict(self):
        d = {"field": "domain", "operator": "eq", "value": "example.com"}
        cond = FilterCondition.from_dict(d)
        assert cond.field == "domain"
        assert cond.operator == FilterOperator.EQUALS
        assert cond.value == "example.com"

    def test_condition_from_dict_with_negate(self):
        d = {"field": "tags", "operator": "contains", "value": "test", "negate": True}
        cond = FilterCondition.from_dict(d)
        assert cond.negate is True


class TestFilterGroup:
    def test_group_with_single_condition(self):
        cond = FilterCondition(field="title", operator=FilterOperator.EQUALS, value="Test")
        group = FilterGroup(logic="AND", conditions=[cond])
        assert group.logic == "AND"
        assert len(group.conditions) == 1

    def test_group_with_multiple_conditions(self):
        c1 = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Python")
        c2 = FilterCondition(field="score", operator=FilterOperator.GREATER_THAN, value=3.0)
        group = FilterGroup(logic="OR", conditions=[c1, c2])
        assert group.logic == "OR"
        assert len(group.conditions) == 2

    def test_nested_groups(self):
        c1 = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Python")
        c2 = FilterCondition(field="score", operator=FilterOperator.GREATER_THAN, value=3.0)
        inner = FilterGroup(logic="OR", conditions=[c1, c2])
        c3 = FilterCondition(field="domain", operator=FilterOperator.EQUALS, value="example.com")
        outer = FilterGroup(logic="AND", conditions=[inner, c3])
        assert len(outer.conditions) == 2

    def test_group_to_dict(self):
        cond = FilterCondition(field="title", operator=FilterOperator.EQUALS, value="Test")
        group = FilterGroup(logic="AND", conditions=[cond])
        d = group.to_dict()
        assert d["logic"] == "AND"
        assert len(d["conditions"]) == 1

    def test_group_from_dict(self):
        d = {
            "logic": "AND",
            "conditions": [
                {"field": "title", "operator": "eq", "value": "Test"}
            ]
        }
        group = FilterGroup.from_dict(d)
        assert group.logic == "AND"
        assert len(group.conditions) == 1


class TestFilterResult:
    def test_default_result(self):
        result = FilterResult()
        assert result.matched is False
        assert result.matched_count == 0
        assert result.items == []

    def test_result_with_items(self):
        result = FilterResult(items=["a", "b"], matched_count=2, total_count=10)
        assert result.matched is True
        assert result.matched_count == 2
        assert result.total_count == 10

    def test_result_to_dict(self):
        result = FilterResult(items=["x"], matched_count=1, total_count=5)
        d = result.to_dict()
        assert d["matched"] is True
        assert d["matched_count"] == 1


class TestDateRangeFilter:
    def test_filter_within_range(self):
        f = DateRangeFilter()
        now = datetime.now(timezone.utc)
        item = {"date": now.isoformat()}
        result = f.apply([item], date_from=(now - timedelta(days=7)).isoformat(), date_to=now.isoformat())
        assert len(result) == 1

    def test_filter_excludes_old(self):
        f = DateRangeFilter()
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=30)).isoformat()
        item = {"date": old}
        result = f.apply([item], date_from=(now - timedelta(days=7)).isoformat())
        assert len(result) == 0

    def test_filter_excludes_future(self):
        f = DateRangeFilter()
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=30)).isoformat()
        item = {"date": future}
        result = f.apply([item], date_to=now.isoformat())
        assert len(result) == 0

    def test_filter_no_date_field(self):
        f = DateRangeFilter()
        item = {"title": "no date"}
        result = f.apply([item], date_from="2020-01-01")
        assert len(result) == 0

    def test_filter_empty_items(self):
        f = DateRangeFilter()
        result = f.apply([], date_from="2020-01-01")
        assert len(result) == 0

    def test_filter_date_from_only(self):
        f = DateRangeFilter()
        now = datetime.now(timezone.utc)
        item = {"date": now.isoformat()}
        result = f.apply([item], date_from=(now - timedelta(days=7)).isoformat())
        assert len(result) == 1

    def test_filter_date_to_only(self):
        f = DateRangeFilter()
        now = datetime.now(timezone.utc)
        item = {"date": now.isoformat()}
        result = f.apply([item], date_to=(now + timedelta(days=7)).isoformat())
        assert len(result) == 1


class TestScoreFilter:
    def test_filter_min_score(self):
        f = ScoreFilter()
        items = [{"score": 8.0}, {"score": 3.0}, {"score": 5.0}]
        result = f.apply(items, min_score=5.0)
        assert len(result) == 2

    def test_filter_max_score(self):
        f = ScoreFilter()
        items = [{"score": 8.0}, {"score": 3.0}, {"score": 5.0}]
        result = f.apply(items, max_score=5.0)
        assert len(result) == 2

    def test_filter_score_range(self):
        f = ScoreFilter()
        items = [{"score": 8.0}, {"score": 3.0}, {"score": 5.0}, {"score": 6.0}]
        result = f.apply(items, min_score=4.0, max_score=7.0)
        assert len(result) == 2

    def test_filter_no_score_field(self):
        f = ScoreFilter()
        items = [{"title": "no score"}]
        result = f.apply(items, min_score=5.0)
        assert len(result) == 0

    def test_filter_empty_items(self):
        f = ScoreFilter()
        result = f.apply([], min_score=5.0)
        assert len(result) == 0

    def test_filter_no_constraints(self):
        f = ScoreFilter()
        items = [{"score": 8.0}, {"score": 3.0}]
        result = f.apply(items)
        assert len(result) == 2


class TestContentTypeFilter:
    def test_filter_by_type(self):
        f = ContentTypeFilter()
        items = [
            {"content_type": "article"},
            {"content_type": "video"},
            {"content_type": "article"},
        ]
        result = f.apply(items, content_types=["article"])
        assert len(result) == 2

    def test_filter_multiple_types(self):
        f = ContentTypeFilter()
        items = [
            {"content_type": "article"},
            {"content_type": "video"},
            {"content_type": "image"},
        ]
        result = f.apply(items, content_types=["article", "video"])
        assert len(result) == 2

    def test_filter_no_type_field(self):
        f = ContentTypeFilter()
        items = [{"title": "no type"}]
        result = f.apply(items, content_types=["article"])
        assert len(result) == 0

    def test_filter_empty_types(self):
        f = ContentTypeFilter()
        items = [{"content_type": "article"}]
        result = f.apply(items, content_types=[])
        assert len(result) == 1

    def test_filter_case_insensitive(self):
        f = ContentTypeFilter()
        items = [{"content_type": "Article"}]
        result = f.apply(items, content_types=["article"])
        assert len(result) == 1


class TestTagFilter:
    def test_filter_by_tag(self):
        f = TagFilter()
        items = [
            {"tags": ["python", "coding"]},
            {"tags": ["rust", "coding"]},
            {"tags": ["python"]},
        ]
        result = f.apply(items, tags=["python"])
        assert len(result) == 2

    def test_filter_multiple_tags_any(self):
        f = TagFilter()
        items = [
            {"tags": ["python", "coding"]},
            {"tags": ["rust", "coding"]},
            {"tags": ["java"]},
        ]
        result = f.apply(items, tags=["python", "rust"], match_mode="any")
        assert len(result) == 2

    def test_filter_multiple_tags_all(self):
        f = TagFilter()
        items = [
            {"tags": ["python", "coding"]},
            {"tags": ["rust", "coding"]},
            {"tags": ["python", "rust", "coding"]},
        ]
        result = f.apply(items, tags=["python", "rust"], match_mode="all")
        assert len(result) == 1

    def test_filter_no_tags_field(self):
        f = TagFilter()
        items = [{"title": "no tags"}]
        result = f.apply(items, tags=["python"])
        assert len(result) == 0

    def test_filter_empty_tags(self):
        f = TagFilter()
        items = [{"tags": []}]
        result = f.apply(items, tags=["python"])
        assert len(result) == 0

    def test_filter_case_insensitive(self):
        f = TagFilter()
        items = [{"tags": ["Python", "Coding"]}]
        result = f.apply(items, tags=["python"])
        assert len(result) == 1


class TestDomainFilter:
    def test_filter_by_domain(self):
        f = DomainFilter()
        items = [
            {"domain": "python.org"},
            {"domain": "rust-lang.org"},
            {"domain": "python.org"},
        ]
        result = f.apply(items, domains=["python.org"])
        assert len(result) == 2

    def test_filter_exclude_domain(self):
        f = DomainFilter()
        items = [
            {"domain": "python.org"},
            {"domain": "rust-lang.org"},
        ]
        result = f.apply(items, exclude_domains=["python.org"])
        assert len(result) == 1

    def test_filter_no_domain_field(self):
        f = DomainFilter()
        items = [{"title": "no domain"}]
        result = f.apply(items, domains=["python.org"])
        assert len(result) == 0

    def test_filter_empty_domains(self):
        f = DomainFilter()
        items = [{"domain": "python.org"}]
        result = f.apply(items, domains=[])
        assert len(result) == 1

    def test_filter_case_insensitive(self):
        f = DomainFilter()
        items = [{"domain": "Python.Org"}]
        result = f.apply(items, domains=["python.org"])
        assert len(result) == 1


class TestStatusFilter:
    def test_filter_by_status(self):
        f = StatusFilter()
        items = [
            {"status": "active"},
            {"status": "archived"},
            {"status": "active"},
        ]
        result = f.apply(items, statuses=["active"])
        assert len(result) == 2

    def test_filter_exclude_status(self):
        f = StatusFilter()
        items = [
            {"status": "active"},
            {"status": "archived"},
        ]
        result = f.apply(items, exclude_statuses=["archived"])
        assert len(result) == 1

    def test_filter_no_status_field(self):
        f = StatusFilter()
        items = [{"title": "no status"}]
        result = f.apply(items, statuses=["active"])
        assert len(result) == 0

    def test_filter_empty_statuses(self):
        f = StatusFilter()
        items = [{"status": "active"}]
        result = f.apply(items, statuses=[])
        assert len(result) == 1


class TestCombinedFilter:
    def test_combine_date_and_score(self):
        f = CombinedFilter()
        now = datetime.now(timezone.utc)
        items = [
            {"date": now.isoformat(), "score": 8.0},
            {"date": now.isoformat(), "score": 3.0},
            {"date": (now - timedelta(days=30)).isoformat(), "score": 8.0},
        ]
        result = f.apply(items, date_from=(now - timedelta(days=7)).isoformat(), min_score=5.0)
        assert len(result) == 1

    def test_combine_tags_and_domain(self):
        f = CombinedFilter()
        items = [
            {"tags": ["python"], "domain": "python.org"},
            {"tags": ["rust"], "domain": "python.org"},
            {"tags": ["python"], "domain": "rust-lang.org"},
        ]
        result = f.apply(items, tags=["python"], domains=["python.org"])
        assert len(result) == 1

    def test_combine_all_filters(self):
        f = CombinedFilter()
        now = datetime.now(timezone.utc)
        items = [
            {
                "date": now.isoformat(),
                "score": 8.0,
                "content_type": "article",
                "tags": ["python"],
                "domain": "python.org",
                "status": "active",
            },
            {
                "date": now.isoformat(),
                "score": 3.0,
                "content_type": "video",
                "tags": ["rust"],
                "domain": "rust-lang.org",
                "status": "archived",
            },
        ]
        result = f.apply(
            items,
            date_from=(now - timedelta(days=7)).isoformat(),
            min_score=5.0,
            content_types=["article"],
            tags=["python"],
            domains=["python.org"],
            statuses=["active"],
        )
        assert len(result) == 1

    def test_combine_no_filters(self):
        f = CombinedFilter()
        items = [{"title": "test"}]
        result = f.apply(items)
        assert len(result) == 1

    def test_combine_empty_items(self):
        f = CombinedFilter()
        result = f.apply([], tags=["python"])
        assert len(result) == 0


class TestSearchFilter:
    def test_filter_with_condition(self):
        sf = SearchFilter()
        items = [
            {"title": "Python Guide", "score": 8.0, "tags": ["python"]},
            {"title": "Rust Guide", "score": 5.0, "tags": ["rust"]},
        ]
        cond = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Python")
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 1

    def test_filter_with_group(self):
        sf = SearchFilter()
        items = [
            {"title": "Python Guide", "score": 8.0},
            {"title": "Rust Guide", "score": 3.0},
        ]
        c1 = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Python")
        c2 = FilterCondition(field="score", operator=FilterOperator.GREATER_THAN, value=5.0)
        group = FilterGroup(logic="AND", conditions=[c1, c2])
        result = sf.filter(items, groups=[group])
        assert len(result) == 1

    def test_filter_or_group(self):
        sf = SearchFilter()
        items = [
            {"title": "Python Guide", "score": 8.0},
            {"title": "Rust Guide", "score": 3.0},
        ]
        c1 = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Python")
        c2 = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="Rust")
        group = FilterGroup(logic="OR", conditions=[c1, c2])
        result = sf.filter(items, groups=[group])
        assert len(result) == 2

    def test_filter_negated_condition(self):
        sf = SearchFilter()
        items = [
            {"title": "Python Guide", "tags": ["python"]},
            {"title": "Rust Guide", "tags": ["rust"]},
        ]
        cond = FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value="python", negate=True)
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 1

    def test_filter_regex(self):
        sf = SearchFilter()
        items = [
            {"title": "Python 3.11 Guide"},
            {"title": "Rust 1.70 Guide"},
        ]
        cond = FilterCondition(field="title", operator=FilterOperator.REGEX, value=r"Python \d+\.\d+")
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 1

    def test_filter_starts_with(self):
        sf = SearchFilter()
        items = [
            {"title": "Python Guide"},
            {"title": "Guide to Python"},
        ]
        cond = FilterCondition(field="title", operator=FilterOperator.STARTS_WITH, value="Python")
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 1

    def test_filter_in_operator(self):
        sf = SearchFilter()
        items = [
            {"content_type": "article"},
            {"content_type": "video"},
            {"content_type": "image"},
        ]
        cond = FilterCondition(field="content_type", operator=FilterOperator.IN, value=["article", "video"])
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 2

    def test_filter_empty_items(self):
        sf = SearchFilter()
        cond = FilterCondition(field="title", operator=FilterOperator.CONTAINS, value="test")
        result = sf.filter([], conditions=[cond])
        assert len(result) == 0

    def test_filter_no_conditions(self):
        sf = SearchFilter()
        items = [{"title": "test"}]
        result = sf.filter(items)
        assert len(result) == 1

    def test_filter_preserves_order(self):
        sf = SearchFilter()
        items = [
            {"title": "A Guide", "score": 8.0},
            {"title": "B Guide", "score": 9.0},
            {"title": "C Guide", "score": 7.0},
        ]
        cond = FilterCondition(field="score", operator=FilterOperator.GREATER_THAN, value=7.5)
        result = sf.filter(items, conditions=[cond])
        assert len(result) == 2
        assert result[0]["title"] == "A Guide"
