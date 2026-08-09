"""Advanced search filters for content search results."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class FilterOperator(Enum):
    """Supported filter operators."""
    EQUALS = "eq"
    CONTAINS = "contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    EXISTS = "exists"


@dataclass
class FilterCondition:
    """A single filter condition."""
    field: str
    operator: FilterOperator
    value: Any
    negate: bool = False

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "negate": self.negate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FilterCondition":
        op_value = data.get("operator", "eq")
        try:
            operator = FilterOperator(op_value)
        except ValueError:
            operator = FilterOperator.EQUALS
        return cls(
            field=data["field"],
            operator=operator,
            value=data["value"],
            negate=data.get("negate", False),
        )


@dataclass
class FilterGroup:
    """A group of filter conditions with AND/OR logic."""
    logic: str = "AND"
    conditions: List[Union[FilterCondition, "FilterGroup"]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "logic": self.logic,
            "conditions": [
                c.to_dict() if isinstance(c, FilterCondition) else c.to_dict()
                for c in self.conditions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FilterGroup":
        parsed_conditions = []
        for cond_data in data.get("conditions", []):
            if "logic" in cond_data:
                parsed_conditions.append(FilterGroup.from_dict(cond_data))
            else:
                parsed_conditions.append(FilterCondition.from_dict(cond_data))
        return cls(logic=data.get("logic", "AND"), conditions=parsed_conditions)


@dataclass
class FilterResult:
    """Result of applying filters."""
    items: List[Any] = field(default_factory=list)
    matched_count: int = 0
    total_count: int = 0
    applied_filters: List[str] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        return self.matched_count > 0 or len(self.items) > 0

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "matched": self.matched,
            "matched_count": self.matched_count,
            "total_count": self.total_count,
            "applied_filters": self.applied_filters,
        }


class DateRangeFilter:
    """Filter items by date range."""

    def apply(
        self,
        items: List[dict],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[dict]:
        result = []
        for item in items:
            item_date_str = item.get("date", "")
            if not item_date_str:
                continue
            try:
                item_date = datetime.fromisoformat(item_date_str)
            except (ValueError, TypeError):
                continue

            if date_from:
                try:
                    from_date = datetime.fromisoformat(date_from)
                    if item_date < from_date:
                        continue
                except (ValueError, TypeError):
                    continue

            if date_to:
                try:
                    to_date = datetime.fromisoformat(date_to)
                    if item_date > to_date:
                        continue
                except (ValueError, TypeError):
                    continue

            result.append(item)
        return result


class ScoreFilter:
    """Filter items by score range."""

    def apply(
        self,
        items: List[dict],
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
    ) -> List[dict]:
        result = []
        for item in items:
            score = item.get("score")
            if score is None:
                continue
            try:
                score = float(score)
            except (ValueError, TypeError):
                continue

            if min_score is not None and score < min_score:
                continue
            if max_score is not None and score > max_score:
                continue
            result.append(item)
        return result


class ContentTypeFilter:
    """Filter items by content type."""

    def apply(
        self,
        items: List[dict],
        content_types: Optional[List[str]] = None,
    ) -> List[dict]:
        if not content_types:
            return items
        allowed = {t.lower() for t in content_types}
        result = []
        for item in items:
            item_type = item.get("content_type", "")
            if item_type.lower() in allowed:
                result.append(item)
        return result


class TagFilter:
    """Filter items by tags."""

    def apply(
        self,
        items: List[dict],
        tags: Optional[List[str]] = None,
        match_mode: str = "any",
    ) -> List[dict]:
        if not tags:
            return items
        search_tags = {t.lower() for t in tags}
        result = []
        for item in items:
            item_tags = item.get("tags", [])
            if not item_tags:
                continue
            item_tags_lower = {t.lower() for t in item_tags}
            if match_mode == "all":
                if search_tags.issubset(item_tags_lower):
                    result.append(item)
            else:
                if search_tags & item_tags_lower:
                    result.append(item)
        return result


class DomainFilter:
    """Filter items by domain."""

    def apply(
        self,
        items: List[dict],
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[dict]:
        result = items[:]
        if domains:
            allowed = {d.lower() for d in domains}
            result = [i for i in result if i.get("domain", "").lower() in allowed]
        if exclude_domains:
            excluded = {d.lower() for d in exclude_domains}
            result = [i for i in result if i.get("domain", "").lower() not in excluded]
        return result


class StatusFilter:
    """Filter items by status."""

    def apply(
        self,
        items: List[dict],
        statuses: Optional[List[str]] = None,
        exclude_statuses: Optional[List[str]] = None,
    ) -> List[dict]:
        result = items[:]
        if statuses:
            allowed = {s.lower() for s in statuses}
            result = [i for i in result if i.get("status", "").lower() in allowed]
        if exclude_statuses:
            excluded = {s.lower() for s in exclude_statuses}
            result = [i for i in result if i.get("status", "").lower() not in excluded]
        return result


class CombinedFilter:
    """Combine multiple filters to apply all at once."""

    def __init__(self):
        self._filters = [
            ("date", DateRangeFilter()),
            ("score", ScoreFilter()),
            ("content_type", ContentTypeFilter()),
            ("tags", TagFilter()),
            ("domain", DomainFilter()),
            ("status", StatusFilter()),
        ]

    def apply(
        self,
        items: List[dict],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        content_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        tag_match_mode: str = "any",
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        exclude_statuses: Optional[List[str]] = None,
    ) -> List[dict]:
        result = items[:]
        if date_from or date_to:
            result = DateRangeFilter().apply(result, date_from=date_from, date_to=date_to)
        if min_score is not None or max_score is not None:
            result = ScoreFilter().apply(result, min_score=min_score, max_score=max_score)
        if content_types:
            result = ContentTypeFilter().apply(result, content_types=content_types)
        if tags:
            result = TagFilter().apply(result, tags=tags, match_mode=tag_match_mode)
        if domains or exclude_domains:
            result = DomainFilter().apply(result, domains=domains, exclude_domains=exclude_domains)
        if statuses or exclude_statuses:
            result = StatusFilter().apply(result, statuses=statuses, exclude_statuses=exclude_statuses)
        return result


class SearchFilter:
    """Main search filter that evaluates conditions and groups against items."""

    def _evaluate_condition(self, item: dict, condition: FilterCondition) -> bool:
        item_value = item.get(condition.field)
        op = condition.operator

        if op == FilterOperator.EQUALS:
            matched = str(item_value).lower() == str(condition.value).lower()
        elif op == FilterOperator.CONTAINS:
            matched = str(condition.value).lower() in str(item_value).lower()
        elif op == FilterOperator.GREATER_THAN:
            try:
                matched = float(item_value) > float(condition.value)
            except (ValueError, TypeError):
                matched = False
        elif op == FilterOperator.LESS_THAN:
            try:
                matched = float(item_value) < float(condition.value)
            except (ValueError, TypeError):
                matched = False
        elif op == FilterOperator.GREATER_THAN_OR_EQUAL:
            try:
                matched = float(item_value) >= float(condition.value)
            except (ValueError, TypeError):
                matched = False
        elif op == FilterOperator.LESS_THAN_OR_EQUAL:
            try:
                matched = float(item_value) <= float(condition.value)
            except (ValueError, TypeError):
                matched = False
        elif op == FilterOperator.IN:
            values = condition.value if isinstance(condition.value, list) else [condition.value]
            matched = str(item_value).lower() in {str(v).lower() for v in values}
        elif op == FilterOperator.NOT_IN:
            values = condition.value if isinstance(condition.value, list) else [condition.value]
            matched = str(item_value).lower() not in {str(v).lower() for v in values}
        elif op == FilterOperator.STARTS_WITH:
            matched = str(item_value).lower().startswith(str(condition.value).lower())
        elif op == FilterOperator.ENDS_WITH:
            matched = str(item_value).lower().endswith(str(condition.value).lower())
        elif op == FilterOperator.REGEX:
            try:
                matched = bool(re.search(str(condition.value), str(item_value), re.IGNORECASE))
            except re.error:
                matched = False
        elif op == FilterOperator.EXISTS:
            matched = item_value is not None and item_value != ""
        else:
            matched = False

        if condition.negate:
            matched = not matched
        return matched

    def _evaluate_group(self, item: dict, group: FilterGroup) -> bool:
        results = []
        for condition in group.conditions:
            if isinstance(condition, FilterCondition):
                results.append(self._evaluate_condition(item, condition))
            elif isinstance(condition, FilterGroup):
                results.append(self._evaluate_group(item, condition))

        if not results:
            return True
        if group.logic.upper() == "AND":
            return all(results)
        else:
            return any(results)

    def filter(
        self,
        items: List[dict],
        conditions: Optional[List[FilterCondition]] = None,
        groups: Optional[List[FilterGroup]] = None,
    ) -> List[dict]:
        if not items:
            return []

        result = []
        for item in items:
            pass_all = True

            for condition in (conditions or []):
                if not self._evaluate_condition(item, condition):
                    pass_all = False
                    break

            if pass_all:
                for group in (groups or []):
                    if not self._evaluate_group(item, group):
                        pass_all = False
                        break

            if pass_all:
                result.append(item)

        return result
