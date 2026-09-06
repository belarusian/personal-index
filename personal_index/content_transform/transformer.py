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

        Args:
            items: List of content items.

        Returns:
            List of transformed content items.
        """
        return [self.transform(item) for item in items]


def create_field_rename_transformer(
    old_name: str,
    new_name: str,
) -> ContentTransformer:
    """Create a transformer that renames a field.

    Args:
        old_name: Original field name.
        new_name: New field name.

    Returns:
        ContentTransformer that renames the field.
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
    """Create a transformer that filters to specific fields.

    Args:
        fields: Fields to keep.

    Returns:
        ContentTransformer that filters fields.
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
    """Create a transformer that adds a field.

    Args:
        field_name: Name of field to add.
        value: Value to set.

    Returns:
        ContentTransformer that adds the field.
    """
    def fn(content: dict[str, Any]) -> dict[str, Any]:
        result = dict(content)
        result[field_name] = value
        return result

    return ContentTransformer(
        name=f"add_{field_name}",
        transform_fn=fn,
    )
