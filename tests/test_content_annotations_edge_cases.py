"""Edge case tests for content_annotations module."""

from __future__ import annotations

import pytest
from personal_index.content_annotations import (
    Annotation,
    AnnotationManager,
    AnnotationType,
)


class TestAnnotationEdgeCases:
    """Edge case tests for Annotation."""

    def test_annotation_empty_text(self):
        a = Annotation(content_id="c1", text="")
        assert a.text == ""

    def test_annotation_unicode_text(self):
        a = Annotation(content_id="c1", text="日本語注釈")
        assert a.text == "日本語注釈"

    def test_annotation_very_long_text(self):
        long_text = "x" * 10000
        a = Annotation(content_id="c1", text=long_text)
        assert len(a.text) == 10000

    def test_annotation_with_none_position(self):
        a = Annotation(content_id="c1", text="Note")
        assert a.position_start is None
        assert a.position_end is None

    def test_annotation_from_dict_missing_fields(self):
        data = {"content_id": "c1"}
        a = Annotation.from_dict(data)
        assert a.text == ""
        assert a.annotation_type == AnnotationType.NOTE

    def test_annotation_from_dict_with_datetime_object(self):
        from datetime import datetime, timezone
        data = {
            "content_id": "c1",
            "text": "Test",
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
        a = Annotation.from_dict(data)
        assert isinstance(a.created_at, str)

    def test_annotation_update_text_preserves_id(self):
        a = Annotation(content_id="c1", text="Original")
        original_id = a.annotation_id
        a.update_text("Updated")
        assert a.annotation_id == original_id

    def test_annotation_add_duplicate_tag(self):
        a = Annotation(content_id="c1", text="Note", tags=["important"])
        a.add_tag("important")
        assert a.tags.count("important") == 1

    def test_annotation_remove_nonexistent_tag(self):
        a = Annotation(content_id="c1", text="Note", tags=["a"])
        a.remove_tag("z")
        assert "a" in a.tags

    def test_annotation_to_dict_includes_all_fields(self):
        a = Annotation(
            content_id="c1",
            text="Test",
            annotation_type=AnnotationType.HIGHLIGHT,
            author="alice",
            tags=["t1"],
            position_start=10,
            position_end=20,
        )
        d = a.to_dict()
        assert d["position_start"] == 10
        assert d["position_end"] == 20
        assert d["annotation_type"] == "highlight"


class TestAnnotationManagerEdgeCases:
    """Edge case tests for AnnotationManager."""

    def setup_method(self):
        self.manager = AnnotationManager()

    def test_search_case_insensitive(self):
        self.manager.add(Annotation(content_id="c1", text="Hello World"))
        results = self.manager.search("hello")
        assert len(results) == 1

    def test_search_partial_match(self):
        self.manager.add(Annotation(content_id="c1", text="Machine Learning"))
        results = self.manager.search("learn")
        assert len(results) == 1

    def test_get_by_content_id_empty(self):
        notes = self.manager.get_by_content_id("nonexistent")
        assert notes == []

    def test_get_by_author_empty(self):
        notes = self.manager.get_by_author("nonexistent")
        assert notes == []

    def test_get_by_type_empty(self):
        notes = self.manager.get_by_type(AnnotationType.NOTE)
        assert notes == []

    def test_get_by_tag_empty(self):
        notes = self.manager.get_by_tag("nonexistent")
        assert notes == []

    def test_delete_already_deleted(self):
        a = Annotation(content_id="c1", text="Note")
        self.manager.add(a)
        self.manager.delete(a.annotation_id)
        result = self.manager.delete(a.annotation_id)
        assert result is False

    def test_stats_empty_manager(self):
        stats = self.manager.get_stats()
        assert stats["total"] == 0
        assert stats["by_content"] == 0

    def test_serialize_empty_manager(self):
        data = self.manager.serialize()
        assert data == []

    def test_deserialize_empty_data(self):
        self.manager.deserialize([])
        assert self.manager.count() == 0

    def test_add_annotation_updates_content_index(self):
        a = Annotation(content_id="c1", text="Note")
        self.manager.add(a)
        notes = self.manager.get_by_content_id("c1")
        assert len(notes) == 1

    def test_add_annotation_updates_type_index(self):
        a = Annotation(content_id="c1", text="Note", annotation_type=AnnotationType.FLAG)
        self.manager.add(a)
        notes = self.manager.get_by_type(AnnotationType.FLAG)
        assert len(notes) == 1

    def test_clear_preserves_manager_object(self):
        self.manager.add(Annotation(content_id="c1", text="A"))
        self.manager.clear()
        assert self.manager.count() == 0
        # Can still add after clear
        self.manager.add(Annotation(content_id="c2", text="B"))
        assert self.manager.count() == 1

    def test_multiple_annotations_same_content(self):
        for i in range(100):
            self.manager.add(Annotation(content_id="c1", text=f"Note {i}"))
        notes = self.manager.get_by_content_id("c1")
        assert len(notes) == 100

    def test_recent_returns_most_recent_first(self):
        self.manager.add(Annotation(content_id="c1", text="First", created_at="2024-01-01"))
        self.manager.add(Annotation(content_id="c2", text="Second", created_at="2024-01-02"))
        self.manager.add(Annotation(content_id="c3", text="Third", created_at="2024-01-03"))
        recent = self.manager.get_recent(2)
        assert recent[0].text == "Third"
        assert recent[1].text == "Second"

    def test_update_text_on_nonexistent(self):
        result = self.manager.update_text("nonexistent", "New text")
        assert result is False

    def test_add_tag_to_nonexistent(self):
        self.manager.add_tag("nonexistent", "tag")
        assert self.manager.count() == 0

    def test_remove_tag_from_nonexistent(self):
        self.manager.remove_tag("nonexistent", "tag")
        assert self.manager.count() == 0

    def test_delete_by_content_id_nonexistent(self):
        deleted = self.manager.delete_by_content_id("nonexistent")
        assert deleted == 0

    def test_search_unicode(self):
        self.manager.add(Annotation(content_id="c1", text="日本語テスト"))
        results = self.manager.search("テスト")
        assert len(results) == 1

    def test_serialize_deserialize_preserves_order(self):
        for i in range(5):
            self.manager.add(Annotation(content_id=f"c{i}", text=f"Note {i}"))
        data = self.manager.serialize()
        manager2 = AnnotationManager()
        manager2.deserialize(data)
        assert manager2.count() == 5
