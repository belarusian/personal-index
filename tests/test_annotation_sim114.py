"""Tests for TICKET-69: SIM114 fix in annotation.py."""

from personal_index.annotation import AnnotationStore, Annotation, AnnotationType


class TestAnnotationSearch:
    def test_search_by_url(self):
        store = AnnotationStore()
        ann = Annotation(
            annotation_id="a1",
            url="https://example.com/page",
            value="test value",
            annotation_type=AnnotationType.TAG,
        )
        store.add(ann)
        results = store.search("example")
        assert len(results) == 1

    def test_search_by_value(self):
        store = AnnotationStore()
        ann = Annotation(
            annotation_id="a2",
            url="https://example.com/page",
            value="important note",
            annotation_type=AnnotationType.NOTE,
        )
        store.add(ann)
        results = store.search("important")
        assert len(results) == 1

    def test_search_no_match(self):
        store = AnnotationStore()
        ann = Annotation(
            annotation_id="a3",
            url="https://example.com/page",
            value="test value",
            annotation_type=AnnotationType.TAG,
        )
        store.add(ann)
        results = store.search("nonexistent")
        assert len(results) == 0

    def test_search_case_insensitive(self):
        store = AnnotationStore()
        ann = Annotation(
            annotation_id="a4",
            url="https://Example.COM/Page",
            value="Test Value",
            annotation_type=AnnotationType.TAG,
        )
        store.add(ann)
        results = store.search("example")
        assert len(results) == 1
        results = store.search("test")
        assert len(results) == 1
