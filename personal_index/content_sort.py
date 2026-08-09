"""Sort saved content items by various fields."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass as dc_dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SortField(Enum):
    """Fields that can be sorted."""
    TITLE = "title"
    SCORE = "score"
    DATE = "date"
    DOMAIN = "domain"
    CONTENT_TYPE = "content_type"
    TAGS = "tags"
    STATUS = "status"
    LENGTH = "length"
    RELEVANCE = "relevance"


class SortDirection(Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"

    @classmethod
    def from_string(cls, value: str) -> "SortDirection":
        if value.lower() == "asc":
            return cls.ASC
        return cls.DESC


@dc_dataclass
class SortConfig:
    """Configuration for sorting."""
    sort_field: SortField = SortField.SCORE
    direction: SortDirection = SortDirection.DESC
    sort_keys: List["SortConfig"] = dc_field(default_factory=list)

    @property
    def field(self) -> SortField:
        return self.sort_field

    @field.setter
    def field(self, value: SortField):
        self.sort_field = value

    def to_dict(self) -> dict:
        result = {
            "field": self.sort_field.value,
            "direction": self.direction.value,
        }
        if self.sort_keys:
            result["sort_keys"] = [k.to_dict() for k in self.sort_keys]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SortConfig":
        if "sort_keys" in data:
            keys = [cls.from_dict(k) for k in data["sort_keys"]]
            return cls(sort_keys=keys)
        sf_value = data.get("field", "score")
        try:
            sf = SortField(sf_value)
        except ValueError:
            sf = SortField.SCORE
        return cls(
            sort_field=sf,
            direction=SortDirection.from_string(data.get("direction", "desc")),
        )


@dc_dataclass
class SortResult:
    """Result of a sort operation."""
    items: List[Any] = dc_field(default_factory=list)
    sort_field: Optional[SortField] = None
    sort_direction: Optional[SortDirection] = None

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "sort_field": self.sort_field.value if self.sort_field else None,
            "sort_direction": self.sort_direction.value if self.sort_direction else None,
        }


class ContentSorter:
    """Sorts content items by various fields."""

    def _get_sort_key(self, item: dict, sort_field: SortField):
        """Extract sort key value from an item."""
        if sort_field == SortField.TITLE:
            val = item.get("title", "") or ""
            return val.lower()
        elif sort_field == SortField.SCORE:
            val = item.get("score", 0)
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        elif sort_field == SortField.DATE:
            val = item.get("date", "")
            if not val:
                return datetime.min.replace(tzinfo=timezone.utc).isoformat()
            try:
                return datetime.fromisoformat(val).isoformat()
            except (ValueError, TypeError):
                return datetime.min.replace(tzinfo=timezone.utc).isoformat()
        elif sort_field == SortField.DOMAIN:
            val = item.get("domain", "") or ""
            return val.lower()
        elif sort_field == SortField.CONTENT_TYPE:
            val = item.get("content_type", "") or ""
            return val.lower()
        elif sort_field == SortField.TAGS:
            tags = item.get("tags", [])
            if not isinstance(tags, list):
                return 0
            return len(tags)
        elif sort_field == SortField.STATUS:
            val = item.get("status", "") or ""
            return val.lower()
        elif sort_field == SortField.LENGTH:
            content = item.get("content", "") or ""
            return len(content)
        elif sort_field == SortField.RELEVANCE:
            val = item.get("relevance", 0)
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        else:
            return ""

    def sort(
        self,
        items: List[dict],
        sort_field: SortField = SortField.SCORE,
        direction: SortDirection = SortDirection.DESC,
    ) -> List[dict]:
        """Sort items by a single field."""
        reverse = direction == SortDirection.DESC
        return sorted(items, key=lambda item: self._get_sort_key(item, sort_field), reverse=reverse)

    def sort_multi(
        self,
        items: List[dict],
        sort_keys: List[SortConfig],
    ) -> List[dict]:
        """Sort items by multiple fields using stable sort."""
        result = items[:]
        # Apply in reverse order so the first key is the primary sort
        for key_config in reversed(sort_keys):
            reverse = key_config.direction == SortDirection.DESC
            result = sorted(
                result,
                key=lambda item: self._get_sort_key(item, key_config.sort_field),
                reverse=reverse,
            )
        return result

    def sort_with_config(
        self,
        items: List[dict],
        config: SortConfig,
    ) -> List[dict]:
        """Sort items using a SortConfig."""
        if config.sort_keys:
            return self.sort_multi(items, config.sort_keys)
        return self.sort(items, sort_field=config.sort_field, direction=config.direction)
