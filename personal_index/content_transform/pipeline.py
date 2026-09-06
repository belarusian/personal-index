"""Transform pipeline for chaining transformations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_transform.transformer import ContentTransformer


@dataclass
class TransformPipeline:
    """Pipeline that chains multiple transformations.

    Attributes:
        name: Pipeline name.
        transformers: Ordered list of transformers.
    """

    name: str = "default_pipeline"
    transformers: list[ContentTransformer] = field(default_factory=list)

    def add(self, transformer: ContentTransformer) -> TransformPipeline:
        """Add a transformer to the pipeline.

        Args:
            transformer: Transformer to add.

        Returns:
            Self for chaining.
        """
        self.transformers.append(transformer)
        return self

    def transform(self, content: dict[str, Any]) -> dict[str, Any]:
        """Apply all transformers in sequence.

        Returns a NEW dict: the input is copied first and never mutated, and
        the result is not the input object. Transformers run in the order they
        were added; an empty pipeline returns a copy equal to (but not
        identical to) the input.

        Args:
            content: Content item to transform.

        Returns:
            A new transformed content item.
        """
        result = dict(content)
        for transformer in self.transformers:
            result = transformer.transform(result)
        return result

    def transform_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply the pipeline to multiple items.

        Returns a NEW list: the input list is never mutated and the result is
        not the input object. Each item is transformed via self.transform,
        order is preserved, and each output item is a new dict. An empty input
        list yields an empty list (no error).

        Args:
            items: List of content items.

        Returns:
            A new list of transformed content items.
        """
        return [self.transform(item) for item in items]

    def clear(self) -> None:
        """Remove all transformers from the pipeline."""
        self.transformers.clear()

    @property
    def step_count(self) -> int:
        """Number of transformation steps."""
        return len(self.transformers)
