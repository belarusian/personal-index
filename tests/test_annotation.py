"""Tests for content annotation system."""

import pytest
from personal_index.annotation import AnnotationStore, Annotation, AnnotationType


class TestAnnotation:
    def test_creation(self):
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE)
        assert a.annotation_id == "a1"
        assert a.value is None

    def test_update(self):
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE, value="old")
        a.update(value="new")
        assert a.value == "new"
        assert a.updated_at is not None

    def test_to_dict(self):
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.TAG, value="important")
        d = a.to_dict()
        assert d["type"] == "tag"
        assert d["value"] == "important"


class TestAnnotationStore:
    def test_add_and_get(self):
        store = AnnotationStore()
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE)
        store.add(a)
        result = store.get("a1")
        assert result is not None
        assert result.url == "http://example.com"

    def test_get_missing(self):
        store = AnnotationStore()
        assert store.get("missing") is None

    def test_get_by_url(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        store.add(Annotation(annotation_id="a2", url="http://example.com", annotation_type=AnnotationType.TAG))
        results = store.get_by_url("http://example.com")
        assert len(results) == 2

    def test_get_by_type(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        store.add(Annotation(annotation_id="a2", url="http://other.com", annotation_type=AnnotationType.TAG))
        notes = store.get_by_type(AnnotationType.NOTE)
        assert len(notes) == 1

    def test_update(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE, value="old"))
        assert store.update("a1", value="new") is True
        assert store.get("a1").value == "new"

    def test_update_missing(self):
        store = AnnotationStore()
        assert store.update("missing") is False

    def test_remove(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        assert store.remove("a1") is True
        assert store.get("a1") is None

    def test_remove_missing(self):
        store = AnnotationStore()
        assert store.remove("missing") is False

    def test_remove_by_url(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        store.add(Annotation(annotation_id="a2", url="http://example.com", annotation_type=AnnotationType.TAG))
        store.add(Annotation(annotation_id="a3", url="http://other.com", annotation_type=AnnotationType.NOTE))
        count = store.remove_by_url("http://example.com")
        assert count == 2
        assert store.count == 1

    def test_search_by_url(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com/page", annotation_type=AnnotationType.NOTE))
        results = store.search("example")
        assert len(results) == 1

    def test_search_by_value(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE, value="important stuff"))
        results = store.search("important")
        assert len(results) == 1

    def test_count(self):
        store = AnnotationStore()
        assert store.count == 0
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        assert store.count == 1

    def test_get_stats(self):
        store = AnnotationStore()
        store.add(Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE))
        store.add(Annotation(annotation_id="a2", url="http://other.com", annotation_type=AnnotationType.TAG))
        stats = store.get_stats()
        assert stats["total"] == 2
        assert stats["by_type"]["note"] == 1
        assert stats["by_type"]["tag"] == 1
        assert stats["urls_annotated"] == 2
