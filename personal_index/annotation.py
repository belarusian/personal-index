"""Content annotation system for marking and categorizing indexed content."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AnnotationType(str, Enum):
    """Types of annotations that can be applied to content."""

    HIGHLIGHT = "highlight"
    NOTE = "note"
    TAG = "tag"
    RATING = "rating"
    CATEGORY = "category"
    BOOKMARK = "bookmark"
    FLAG = "flag"


@dataclass
class Annotation:
    """A single annotation on content."""

    annotation_id: str
    url: str
    annotation_type: AnnotationType
    value: Any = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float | None = None
    author: str = ""

    def update(self, value: Any = None, metadata: dict | None = None) -> None:
        """Update the annotation value and/or metadata.

        Args:
            value: New value for the annotation.
            metadata: Additional metadata to merge into existing metadata.
        """
        if value is not None:
            self.value = value
        if metadata is not None:
            self.metadata.update(metadata)
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        """Serialize the annotation to a dictionary.

        Returns:
            Dictionary representation of the annotation.
        """
        return {
            "annotation_id": self.annotation_id,
            "url": self.url,
            "type": self.annotation_type.value,
            "value": self.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "author": self.author,
        }


class AnnotationStore:
    """Stores and manages annotations."""

    def __init__(self):
        self._annotations: dict[str, Annotation] = {}
        self._by_url: dict[str, list[str]] = {}

    def add(self, annotation: Annotation) -> None:
        """Add an annotation to the store.

        Args:
            annotation: The annotation to add.
        """
        self._annotations[annotation.annotation_id] = annotation
        if annotation.url not in self._by_url:
            self._by_url[annotation.url] = []
        if annotation.annotation_id not in self._by_url[annotation.url]:
            self._by_url[annotation.url].append(annotation.annotation_id)

    def get(self, annotation_id: str) -> Annotation | None:
        """Get an annotation by its ID.

        Args:
            annotation_id: The ID of the annotation.

        Returns:
            The annotation, or None if not found.
        """
        return self._annotations.get(annotation_id)

    def get_by_url(self, url: str) -> list[Annotation]:
        """Get all annotations for a given URL.

        Args:
            url: The URL to look up.

        Returns:
            List of annotations associated with the URL.
        """
        ids = self._by_url.get(url, [])
        return [self._annotations[aid] for aid in ids if aid in self._annotations]

    def get_by_type(self, annotation_type: AnnotationType) -> list[Annotation]:
        """Get all annotations of a given type.

        Args:
            annotation_type: The type to filter by.

        Returns:
            List of matching annotations.
        """
        return [a for a in self._annotations.values() if a.annotation_type == annotation_type]

    def update(self, annotation_id: str, value: Any = None, metadata: dict | None = None) -> bool:
        """Update an existing annotation by ID.

        Args:
            annotation_id: The ID of the annotation to update.
            value: New value for the annotation.
            metadata: Additional metadata to merge.

        Returns:
            True if the annotation was found and updated, False otherwise.
        """
        annotation = self._annotations.get(annotation_id)
        if annotation:
            annotation.update(value, metadata)
            return True
        return False

    def remove(self, annotation_id: str) -> bool:
        """Remove an annotation by ID.

        Args:
            annotation_id: The ID of the annotation to remove.

        Returns:
            True if the annotation was found and removed, False otherwise.
        """
        annotation = self._annotations.pop(annotation_id, None)
        if annotation:
            if annotation.url in self._by_url:
                self._by_url[annotation.url] = [
                    aid for aid in self._by_url[annotation.url] if aid != annotation_id
                ]
            return True
        return False

    def remove_by_url(self, url: str) -> int:
        """Remove all annotations for a given URL.

        Args:
            url: The URL whose annotations should be removed.

        Returns:
            The number of annotations removed.
        """
        ids = self._by_url.pop(url, [])
        count = 0
        for aid in ids:
            if aid in self._annotations:
                del self._annotations[aid]
                count += 1
        return count

    def search(self, query: str) -> list[Annotation]:
        """Search annotations by URL or value."""
        query_lower = query.lower()
        results = []
        for annotation in self._annotations.values():
            if query_lower in annotation.url.lower() or (
                isinstance(annotation.value, str) and query_lower in annotation.value.lower()
            ):
                results.append(annotation)
        return results

    @property
    def count(self) -> int:
        """Total number of annotations in the store."""
        return len(self._annotations)

    def get_stats(self) -> dict:
        """Get statistics about the annotation store.

        Returns:
            Dictionary with total count, counts by type, and number of annotated URLs.
        """
        type_counts = {}
        for annotation in self._annotations.values():
            t = annotation.annotation_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "total": self.count,
            "by_type": type_counts,
            "urls_annotated": len(self._by_url),
        }
