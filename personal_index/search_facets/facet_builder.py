"""Build facets from document collections."""

from __future__ import annotations

from typing import Any

from personal_index.search_facets.facet import Facet, FacetType


class FacetBuilder:
    """Builds facet dimensions from a collection of documents."""

    DEFAULT_FACET_TYPES: dict[str, FacetType] = {
        "tags": FacetType.TAG,
        "category": FacetType.CATEGORY,
        "date": FacetType.DATE,
        "domain": FacetType.STRING,
        "author": FacetType.STRING,
        "status": FacetType.CATEGORY,
        "score": FacetType.NUMBER,
        "enabled": FacetType.BOOLEAN,
    }

    def build(
        self,
        items: list[dict[str, Any]],
        facet_fields: list[str],
        max_values: int = 50,
        facet_types: dict[str, str] | None = None,
    ) -> dict[str, Facet]:
        """Build facets from a list of document items."""
        if not items:
            return {}

        facets: dict[str, Facet] = {}
        custom_types = facet_types or {}

        for field_name in facet_fields:
            facet_type = self._resolve_facet_type(field_name, custom_types)
            facet = Facet(name=field_name, facet_type=facet_type)

            for item in items:
                values = self._extract_values(item, field_name)
                for value in values:
                    facet.add_value(str(value))

            if not facet.values:
                continue

            facet.sort_values()
            facet.values = facet.values[:max_values]
            facets[field_name] = facet

        return facets

    def aggregate(
        self,
        facets_a: dict[str, Facet],
        facets_b: dict[str, Facet],
    ) -> dict[str, Facet]:
        """Aggregate two facet dictionaries."""
        merged: dict[str, Facet] = {}

        all_keys = set(facets_a.keys()) | set(facets_b.keys())
        for key in all_keys:
            fa = facets_a.get(key)
            fb = facets_b.get(key)

            if fa and fb:
                merged_facet = Facet(name=key, facet_type=fa.facet_type)
                all_values: dict[str, int] = {}
                for v in fa.values:
                    all_values[v.name] = all_values.get(v.name, 0) + v.count
                for v in fb.values:
                    all_values[v.name] = all_values.get(v.name, 0) + v.count
                for name, count in sorted(all_values.items(), key=lambda x: x[1], reverse=True):
                    merged_facet.add_value(name, count=0)
                    merged_facet.values[-1].count = count
                merged[key] = merged_facet
            elif fa:
                merged[key] = fa
            elif fb:
                merged[key] = fb

        return merged

    def _resolve_facet_type(self, field_name: str, custom_types: dict[str, str]) -> FacetType:
        """Resolve the facet type for a field."""
        base_name = field_name.split(".")[-1]
        type_str = custom_types.get(field_name, custom_types.get(base_name, ""))
        if type_str:
            try:
                return FacetType(type_str)
            except ValueError:
                pass
        return self.DEFAULT_FACET_TYPES.get(base_name, FacetType.STRING)

    def _extract_values(self, item: dict[str, Any], field_name: str) -> list[Any]:
        """Extract values from a nested field path."""
        parts = field_name.split(".")
        current: Any = item
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []

        if isinstance(current, list):
            return current
        elif current is not None:
            return [current]
        return []
