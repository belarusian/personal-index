"""Facet data models for filterable search dimensions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FacetType(Enum):
    """Type of facet dimension."""

    CATEGORY = "category"
    TAG = "tag"
    DATE = "date"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


@dataclass
class FacetValue:
    """A single value within a facet."""

    name: str
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "count": self.count}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FacetValue:
        return cls(name=data["name"], count=data.get("count", 0))


@dataclass
class Facet:
    """A filterable search dimension with values."""

    name: str
    facet_type: FacetType = FacetType.STRING
    values: list[FacetValue] = field(default_factory=list)

    def add_value(self, name: str, count: int = 1) -> None:
        """Add or update a facet value in place.

        If a value with the same ``name`` already exists in ``self.values``,
        its ``count`` is incremented by ``count`` (``existing.count += count``);
        it is never replaced. Otherwise a new ``FacetValue(name, count)`` is
        appended to ``self.values``. ``count`` defaults to ``1`` when omitted.
        Mutates ``self.values`` and returns ``None``.
        """
        existing = next((v for v in self.values if v.name == name), None)
        if existing:
            existing.count += count
        else:
            self.values.append(FacetValue(name=name, count=count))

    def sort_values(self) -> None:
        """Sort ``self.values`` in place by ``count`` descending.

        Sorts the list in place (mutates ``self.values``; does not return a new
        list). The key is ``count`` with ``reverse=True``, so the highest count
        comes first. Python's sort is stable, so values with equal ``count``
        preserve their prior (insertion) relative order. Returns ``None``.
        """
        self.values.sort(key=lambda v: v.count, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "facet_type": self.facet_type.value,
            "values": [v.to_dict() for v in self.values],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Facet:
        ft = data.get("facet_type", "string")
        if isinstance(ft, str):
            ft = FacetType(ft)
        values = [FacetValue.from_dict(v) for v in data.get("values", [])]
        return cls(name=data["name"], facet_type=ft, values=values)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Facet):
            return NotImplemented
        return self.name == other.name and self.facet_type == other.facet_type
