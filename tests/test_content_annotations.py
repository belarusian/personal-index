"""Tests for content_annotations module - user notes on saved items."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from personal_index.content_annotations import (
    Annotation,
    AnnotationManager,
    AnnotationType,
)


class TestAnnotation:
    """Tests for Annotation dataclass."""

    def test_create_annotation_basic(self):
        a = Annotation(content_id="c1", text="Important page")
        assert a.content_id == "c1"
        assert a.text == "Important page"
        assert a.annotation_type == AnnotationType.NOTE
        assert a.created_at is not None

    def test_create_annotation_with_type(self):
        a = Annotation(
            content_id="c1",
            text="Highlight",
            annotation_type=AnnotationType.HIGHLIGHT,
        )
        assert a.annotation_type == AnnotationType.HIGHLIGHT

    def test_create_annotation_with_author(self):
        a = Annotation(
            content_id="c1",
            text="My note",
            author="alice",
        )
        assert a.author == "alice"

    def test_create_annotation_with_tags(self):
        a = Annotation(
            content_id="c1",
            text="Research material",
            tags=["research", "important"],
        )
        assert a.tags == ["research", "important"]

    def test_create_annotation_with_position(self):
        a = Annotation(
            content_id="c1",
            text="Key quote",
            position_start=100,
            position_end=200,
        )
        assert a.position_start == 100
        assert a.position_end == 200

    def test_annotation_to_dict(self):
        a = Annotation(
            content_id="c1",
            text="Test note",
            author="bob",
            tags=["tag1"],
        )
        d = a.to_dict()
        assert d["content_id"] == "c1"
        assert d["text"] == "Test note"
        assert d["author"] == "bob"
        assert d["tags"] == ["tag1"]

    def test_annotation_from_dict(self):
        data = {
            "annotation_id": "a1",
            "content_id": "c1",
            "text": "Test",
            "annotation_type": "note",
            "author": "alice",
            "tags": ["t1"],
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
        }
        a = Annotation.from_dict(data)
        assert a.annotation_id == "a1"
        assert a.content_id == "c1"
        assert a.text == "Test"
        assert a.annotation_type == AnnotationType.NOTE
        assert a.author == "alice"

    def test_annotation_from_dict_defaults(self):
        data = {"content_id": "c1", "text": "Hi"}
        a = Annotation.from_dict(data)
        assert a.annotation_type == AnnotationType.NOTE
        assert a.author == ""
        assert a.tags == []

    def test_annotation_update_text(self):
        a = Annotation(content_id="c1", text="Original")
        a.update_text("Updated")
        assert a.text == "Updated"
        assert a.updated_at is not None

    def test_annotation_update_tags(self):
        a = Annotation(content_id="c1", text="Note", tags=["a"])
        a.add_tag("b")
        assert "b" in a.tags
        a.remove_tag("a")
        assert "a" not in a.tags

    def test_annotation_serialization_roundtrip(self):
        a = Annotation(
            content_id="c1",
            text="Round trip",
            author="test",
            tags=["x", "y"],
            annotation_type=AnnotationType.HIGHLIGHT,
        )
        d = a.to_dict()
        a2 = Annotation.from_dict(d)
        assert a2.content_id == a.content_id
        assert a2.text == a.text
        assert a2.author == a.author
        assert a2.tags == a.tags
        assert a2.annotation_type == a.annotation_type


class TestAnnotationType:
    """Tests for AnnotationType enum."""

    def test_all_types_exist(self):
        assert AnnotationType.NOTE.value == "note"
        assert AnnotationType.HIGHLIGHT.value == "highlight"
        assert AnnotationType.TAG.value == "tag"
        assert AnnotationType.RATING.value == "rating"
        assert AnnotationType.FLAG.value == "flag"

    def test_type_from_string(self):
        assert AnnotationType("note") == AnnotationType.NOTE
        assert AnnotationType("highlight") == AnnotationType.HIGHLIGHT

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            AnnotationType("invalid_type")


class TestAnnotationManager:
    """Tests for AnnotationManager."""

    def setup_method(self):
        self.manager = AnnotationManager()

    def test_add_annotation(self):
        a = Annotation(content_id="c1", text="Note 1")
        self.manager.add(a)
        assert self.manager.count() == 1

    def test_add_multiple_annotations(self):
        for i in range(5):
            self.manager.add(Annotation(content_id="c1", text=f"Note {i}"))
        assert self.manager.count() == 5

    def test_get_annotation_by_id(self):
        a = Annotation(content_id="c1", text="Find me")
        self.manager.add(a)
        found = self.manager.get(a.annotation_id)
        assert found is not None
        assert found.text == "Find me"

    def test_get_nonexistent_annotation(self):
        found = self.manager.get("nonexistent")
        assert found is None

    def test_get_annotations_by_content_id(self):
        self.manager.add(Annotation(content_id="c1", text="Note A"))
        self.manager.add(Annotation(content_id="c1", text="Note B"))
        self.manager.add(Annotation(content_id="c2", text="Note C"))
        notes = self.manager.get_by_content_id("c1")
        assert len(notes) == 2

    def test_get_annotations_by_author(self):
        self.manager.add(Annotation(content_id="c1", text="A", author="alice"))
        self.manager.add(Annotation(content_id="c2", text="B", author="bob"))
        self.manager.add(Annotation(content_id="c3", text="C", author="alice"))
        notes = self.manager.get_by_author("alice")
        assert len(notes) == 2

    def test_get_annotations_by_type(self):
        self.manager.add(Annotation(content_id="c1", text="H", annotation_type=AnnotationType.HIGHLIGHT))
        self.manager.add(Annotation(content_id="c2", text="N", annotation_type=AnnotationType.NOTE))
        highlights = self.manager.get_by_type(AnnotationType.HIGHLIGHT)
        assert len(highlights) == 1

    def test_update_annotation(self):
        a = Annotation(content_id="c1", text="Original")
        self.manager.add(a)
        self.manager.update_text(a.annotation_id, "Updated")
        found = self.manager.get(a.annotation_id)
        assert found.text == "Updated"

    def test_update_nonexistent_annotation(self):
        result = self.manager.update_text("nonexistent", "New text")
        assert result is False

    def test_delete_annotation(self):
        a = Annotation(content_id="c1", text="To delete")
        self.manager.add(a)
        self.manager.delete(a.annotation_id)
        assert self.manager.count() == 0

    def test_delete_nonexistent_annotation(self):
        result = self.manager.delete("nonexistent")
        assert result is False

    def test_delete_by_content_id(self):
        self.manager.add(Annotation(content_id="c1", text="A"))
        self.manager.add(Annotation(content_id="c1", text="B"))
        self.manager.add(Annotation(content_id="c2", text="C"))
        deleted = self.manager.delete_by_content_id("c1")
        assert deleted == 2
        assert self.manager.count() == 1

    def test_search_annotations(self):
        self.manager.add(Annotation(content_id="c1", text="Important research"))
        self.manager.add(Annotation(content_id="c2", text="Casual reading"))
        results = self.manager.search("research")
        assert len(results) == 1
        assert results[0].text == "Important research"

    def test_search_no_results(self):
        self.manager.add(Annotation(content_id="c1", text="Hello"))
        results = self.manager.search("xyz")
        assert len(results) == 0

    def test_get_recent_annotations(self):
        for i in range(10):
            self.manager.add(Annotation(content_id=f"c{i}", text=f"Note {i}"))
        recent = self.manager.get_recent(5)
        assert len(recent) == 5

    def test_get_all_annotations(self):
        self.manager.add(Annotation(content_id="c1", text="A"))
        self.manager.add(Annotation(content_id="c2", text="B"))
        all_notes = self.manager.get_all()
        assert len(all_notes) == 2

    def test_get_stats(self):
        self.manager.add(Annotation(content_id="c1", text="A", annotation_type=AnnotationType.NOTE))
        self.manager.add(Annotation(content_id="c2", text="B", annotation_type=AnnotationType.HIGHLIGHT))
        self.manager.add(Annotation(content_id="c3", text="C", annotation_type=AnnotationType.NOTE))
        stats = self.manager.get_stats()
        assert stats["total"] == 3
        assert stats["by_content"] == 3
        assert stats["by_type"]["note"] == 2
        assert stats["by_type"]["highlight"] == 1

    def test_add_tag_to_annotation(self):
        a = Annotation(content_id="c1", text="Note")
        self.manager.add(a)
        self.manager.add_tag(a.annotation_id, "important")
        found = self.manager.get(a.annotation_id)
        assert "important" in found.tags

    def test_remove_tag_from_annotation(self):
        a = Annotation(content_id="c1", text="Note", tags=["a", "b"])
        self.manager.add(a)
        self.manager.remove_tag(a.annotation_id, "a")
        found = self.manager.get(a.annotation_id)
        assert "a" not in found.tags
        assert "b" in found.tags

    def test_get_annotations_with_tag(self):
        self.manager.add(Annotation(content_id="c1", text="A", tags=["important"]))
        self.manager.add(Annotation(content_id="c2", text="B", tags=["casual"]))
        self.manager.add(Annotation(content_id="c3", text="C", tags=["important"]))
        tagged = self.manager.get_by_tag("important")
        assert len(tagged) == 2

    def test_clear_all(self):
        self.manager.add(Annotation(content_id="c1", text="A"))
        self.manager.add(Annotation(content_id="c2", text="B"))
        self.manager.clear()
        assert self.manager.count() == 0

    def test_serialize_deserialize(self):
        self.manager.add(Annotation(content_id="c1", text="A", author="alice"))
        self.manager.add(Annotation(content_id="c2", text="B", author="bob"))
        data = self.manager.serialize()
        manager2 = AnnotationManager()
        manager2.deserialize(data)
        assert manager2.count() == 2
        assert manager2.get_by_author("alice")
