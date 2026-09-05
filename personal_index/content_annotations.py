"""Content annotations module - user notes on saved items."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AnnotationType(str, Enum):
    """Types of annotations users can add to content."""

    NOTE = "note"
    HIGHLIGHT = "highlight"
    TAG = "tag"
    RATING = "rating"
    FLAG = "flag"


@dataclass
class Annotation:
    """A user annotation on a saved content item."""

    content_id: str
    text: str
    annotation_type: AnnotationType = AnnotationType.NOTE
    annotation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    author: str = ""
    tags: list[str] = field(default_factory=list)
    position_start: int | None = None
    position_end: int | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str | None = None

    def update_text(self, new_text: str) -> None:
        """Update the annotation text."""
        self.text = new_text
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_tag(self, tag: str) -> None:
        """Add a tag to this annotation."""
        if tag not in self.tags:
            self.tags.append(tag)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this annotation."""
        if tag in self.tags:
            self.tags.remove(tag)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "annotation_id": self.annotation_id,
            "content_id": self.content_id,
            "text": self.text,
            "annotation_type": self.annotation_type.value,
            "author": self.author,
            "tags": list(self.tags),
            "position_start": self.position_start,
            "position_end": self.position_end,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Annotation:
        """Deserialize from dictionary."""
        atype = data.get("annotation_type", "note")
        if isinstance(atype, str):
            atype = AnnotationType(atype)
        elif not isinstance(atype, AnnotationType):
            atype = AnnotationType.NOTE

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            annotation_id=data.get("annotation_id", uuid.uuid4().hex[:12]),
            content_id=data["content_id"],
            text=data.get("text", ""),
            annotation_type=atype,
            author=data.get("author", ""),
            tags=data.get("tags", []),
            position_start=data.get("position_start"),
            position_end=data.get("position_end"),
            created_at=created_at,
            updated_at=data.get("updated_at"),
        )


class AnnotationManager:
    """Manages user annotations on saved content items."""

    def __init__(self) -> None:
        """Initialize the annotation manager with empty storage."""
        self._annotations: dict[str, Annotation] = {}
        self._by_content: dict[str, list[str]] = {}
        self._by_author: dict[str, list[str]] = {}
        self._by_type: dict[str, list[str]] = {}
        self._by_tag: dict[str, list[str]] = {}

    def add(self, annotation: Annotation) -> None:
        """Add an annotation and update all five lookup indexes.

        Indexes updated, in order:
        1. ``_annotations[annotation.annotation_id]`` is set to the
           annotation (always).
        2. ``annotation.annotation_id`` is appended to
           ``_by_content[annotation.content_id]`` (always).
        3. ``annotation.annotation_id`` is appended to
           ``_by_author[annotation.author]`` ONLY when ``annotation.author``
           is truthy; a falsy author leaves ``_by_author`` untouched.
        4. ``annotation.annotation_id`` is appended to
           ``_by_type[annotation.annotation_type.value]`` (always).
        5. ``annotation.annotation_id`` is appended to ``_by_tag[tag]`` for
           each ``tag`` in ``annotation.tags``.

        Returns None.
        """
        self._annotations[annotation.annotation_id] = annotation

        cid = annotation.content_id
        if cid not in self._by_content:
            self._by_content[cid] = []
        self._by_content[cid].append(annotation.annotation_id)

        if annotation.author:
            author = annotation.author
            if author not in self._by_author:
                self._by_author[author] = []
            self._by_author[author].append(annotation.annotation_id)

        type_key = annotation.annotation_type.value
        if type_key not in self._by_type:
            self._by_type[type_key] = []
        self._by_type[type_key].append(annotation.annotation_id)

        for tag in annotation.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(annotation.annotation_id)

    def get(self, annotation_id: str) -> Annotation | None:
        """Get an annotation by ID."""
        return self._annotations.get(annotation_id)

    def get_by_content_id(self, content_id: str) -> list[Annotation]:
        """Get all annotations for a content item."""
        ids = self._by_content.get(content_id, [])
        return [self._annotations[i] for i in ids if i in self._annotations]

    def get_by_author(self, author: str) -> list[Annotation]:
        """Get all annotations by a specific author."""
        ids = self._by_author.get(author, [])
        return [self._annotations[i] for i in ids if i in self._annotations]

    def get_by_type(self, annotation_type: AnnotationType) -> list[Annotation]:
        """Get all annotations of a specific type."""
        type_key = annotation_type.value
        ids = self._by_type.get(type_key, [])
        return [self._annotations[i] for i in ids if i in self._annotations]

    def get_by_tag(self, tag: str) -> list[Annotation]:
        """Get all annotations with a specific tag."""
        ids = self._by_tag.get(tag, [])
        return [self._annotations[i] for i in ids if i in self._annotations]

    def get_all(self) -> list[Annotation]:
        """Get all annotations."""
        return list(self._annotations.values())

    def get_recent(self, limit: int = 10) -> list[Annotation]:
        """Return up to `limit` annotations (default 10), sorted by
        `created_at` in descending order (newest first)."""
        all_ann = list(self._annotations.values())
        all_ann.sort(key=lambda a: a.created_at, reverse=True)
        return all_ann[:limit]

    def update_text(self, annotation_id: str, new_text: str) -> bool:
        """Update the text of an annotation."""
        ann = self._annotations.get(annotation_id)
        if ann:
            ann.update_text(new_text)
            return True
        return False

    def add_tag(self, annotation_id: str, tag: str) -> None:
        """Add a tag to an annotation."""
        ann = self._annotations.get(annotation_id)
        if ann:
            ann.add_tag(tag)
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(annotation_id)

    def remove_tag(self, annotation_id: str, tag: str) -> None:
        """Remove a tag from an annotation."""
        ann = self._annotations.get(annotation_id)
        if ann:
            ann.remove_tag(tag)
            if tag in self._by_tag:
                self._by_tag[tag] = [
                    i for i in self._by_tag[tag] if i != annotation_id
                ]

    def delete(self, annotation_id: str) -> bool:
        """Delete an annotation."""
        ann = self._annotations.pop(annotation_id, None)
        if ann:
            # Remove from content index
            cid = ann.content_id
            if cid in self._by_content:
                self._by_content[cid] = [
                    i for i in self._by_content[cid] if i != annotation_id
                ]
            # Remove from author index
            if ann.author in self._by_author:
                self._by_author[ann.author] = [
                    i for i in self._by_author[ann.author] if i != annotation_id
                ]
            # Remove from type index
            type_key = ann.annotation_type.value
            if type_key in self._by_type:
                self._by_type[type_key] = [
                    i for i in self._by_type[type_key] if i != annotation_id
                ]
            # Remove from tag index
            for tag in ann.tags:
                if tag in self._by_tag:
                    self._by_tag[tag] = [
                        i for i in self._by_tag[tag] if i != annotation_id
                    ]
            return True
        return False

    def delete_by_content_id(self, content_id: str) -> int:
        """Delete all annotations for a content item. Returns count deleted."""
        ids = self._by_content.pop(content_id, [])
        count = 0
        for aid in ids:
            if self.delete(aid):
                count += 1
        return count

    def search(self, query: str) -> list[Annotation]:
        """Search annotations by text content."""
        query_lower = query.lower()
        results = []
        for ann in self._annotations.values():
            if query_lower in ann.text.lower():
                results.append(ann)
        return results

    def count(self) -> int:
        """Return total number of annotations."""
        return len(self._annotations)

    def get_stats(self) -> dict:
        """Get annotation statistics."""
        by_type: dict[str, int] = {}
        for ann in self._annotations.values():
            t = ann.annotation_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total": len(self._annotations),
            "by_content": len(self._by_content),
            "by_type": by_type,
        }

    def clear(self) -> None:
        """Remove all annotations."""
        self._annotations.clear()
        self._by_content.clear()
        self._by_author.clear()
        self._by_type.clear()
        self._by_tag.clear()

    def serialize(self) -> list[dict]:
        """Serialize all annotations to a list of dicts."""
        return [ann.to_dict() for ann in self._annotations.values()]

    def deserialize(self, data: list[dict]) -> None:
        """Deserialize annotations from a list of dicts."""
        self.clear()
        for item in data:
            ann = Annotation.from_dict(item)
            self.add(ann)
