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

        Args:
            content: Content item to transform.

        Returns:
            Transformed content item.
        """
        result = dict(content)
        for transformer in self.transformers:
            result = transformer.transform(result)
        return result

    def transform_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply pipeline to multiple items.

        Args:
            items: List of content items.

        Returns:
            List of transformed content items.
        """
        return [self.transform(item) for item in items]

    def clear(self) -> None:
        """Remove all transformers from the pipeline."""
        self.transformers.clear()

    @property
    def step_count(self) -> int:
        """Number of transformation steps."""
        return len(self.transformers)
