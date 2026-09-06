"""Content transformation operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContentTransformer:
    """Applies transformations to content items.

    Attributes:
        name: Transformer name.
        transform_fn: Function that transforms content.
    """

    name: str = "default"
    transform_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None

    def transform(self, content: dict[str, Any]) -> dict[str, Any]:
        """Transform a content item.

        If ``transform_fn`` is set, it is called with ``content`` and its
        return value is returned. If ``transform_fn`` is None, a shallow
        copy of the input dict is returned unchanged (not the same object,
        same contents).

        Args:
            content: Content item to transform.

        Returns:
            Transformed content item, or a shallow copy when no
            ``transform_fn`` is set.
        """
        if self.transform_fn:
            return self.transform_fn(content)
        return dict(content)

    def transform_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform multiple content items.

        Each item is transformed via ``self.transform(item)`` and the results
        are collected into a NEW list (list comprehension), so the input list
        is never mutated and the returned list is not the input object. Item
        order is preserved. An empty input list yields an empty list (no
        error).

        Args:
            items: List of content items.

        Returns:
            A new list of transformed content items, in the same order as
            ``items``.
        """
        return [self.transform(item) for item in items]


def create_field_rename_transformer(
    old_name: str,
    new_name: str,
) -> ContentTransformer:
    """Create a transformer that renames a field (move, not copy).

    Behavior:
        - Returns a NEW dict (shallow copy); the input dict is never mutated.
        - If old_name is present in content, it is MOVED to new_name
          (pop old_name, set new_name). The old key disappears.
        - If old_name is absent, content is returned unchanged (no-op, no error,
          no new key is created).

    Args:
        old_name: Original field name to rename from.
        new_name: New field name to rename to.

    Returns:
        ContentTransformer named rename_{old_name}_to_{new_name}.
    """
    def fn(content: dict[str, Any]) -> dict[str, Any]:
        result = dict(content)
        if old_name in result:
            result[new_name] = result.pop(old_name)
        return result

    return ContentTransformer(
        name=f"rename_{old_name}_to_{new_name}",
        transform_fn=fn,
    )


def create_field_filter_transformer(
    fields: list[str],
) -> ContentTransformer:
    """Create a transformer that filters content down to specific fields.

    The returned transformer's transform returns a NEW dict (a dict
    comprehension over the input, so the input dict is never mutated) keeping
    only the keys present in ``fields``; the input's key order is preserved.
    If no key matches ``fields`` (or ``fields`` is empty) an empty dict is
    returned (no error). The transformer is named
    ``filter_fields_{len(fields)}``.

    Args:
        fields: Fields to keep.

    Returns:
        ContentTransformer named ``filter_fields_{len(fields)}`` that keeps
        only the listed fields.
    """
    def fn(content: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in content.items() if k in fields}

    return ContentTransformer(
        name=f"filter_fields_{len(fields)}",
        transform_fn=fn,
    )


def create_field_add_transformer(
    field_name: str,
    value: Any,
) -> ContentTransformer:
    """Create a transformer that sets a field (add-or-overwrite).

    The returned transformer's transform returns a NEW dict (a shallow copy of
    the input, so the input dict is never mutated) with ``field_name`` set to
    ``value``. If ``field_name`` already exists in the content it is
    OVERWRITTEN with ``value``; if absent it is added. The transformer is named
    ``add_{field_name}``.

    Args:
        field_name: Name of the field to set.
        value: Value to set the field to.

    Returns:
        ContentTransformer named ``add_{field_name}`` that sets the field.
    """
    def fn(content: dict[str, Any]) -> dict[str, Any]:
        result = dict(content)
        result[field_name] = value
        return result

    return ContentTransformer(
        name=f"add_{field_name}",
        transform_fn=fn,
    )
