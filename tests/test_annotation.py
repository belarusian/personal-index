"""Tests for content annotation system."""

from personal_index.annotation import Annotation, AnnotationStore, AnnotationType


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


class TestAnnotationAddCollision:
    def test_add_new_annotation_indexes_under_url(self):
        store = AnnotationStore()
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE)
        store.add(a)
        assert store.get("a1") is a
        assert a in store.get_by_url("http://example.com")

    def test_add_id_collision_reconciles_url_index(self):
        store = AnnotationStore()
        old = Annotation(annotation_id="a1", url="http://old.example.com", annotation_type=AnnotationType.NOTE, created_at=100.0)
        store.add(old)
        new = Annotation(annotation_id="a1", url="http://new.example.com", annotation_type=AnnotationType.NOTE, created_at=200.0)
        store.add(new)
        # id reachable from exactly one URL (the new one)
        assert new in store.get_by_url("http://new.example.com")
        assert old not in store.get_by_url("http://old.example.com")
        assert new not in store.get_by_url("http://old.example.com")
        # registry holds the new object, created_at preserved
        assert store.get("a1") is new
        assert store.get("a1").url == "http://new.example.com"
        assert store.get("a1").created_at == 200.0
        # id appears in exactly one URL's index list
        urls_with_id = [u for u, ids in store._by_url.items() if "a1" in ids]
        assert urls_with_id == ["http://new.example.com"]

    def test_add_id_collision_same_url_no_duplicate(self):
        store = AnnotationStore()
        a = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE, created_at=100.0)
        store.add(a)
        b = Annotation(annotation_id="a1", url="http://example.com", annotation_type=AnnotationType.NOTE, created_at=300.0)
        store.add(b)
        # no duplicate entry in the index list
        assert store._by_url["http://example.com"].count("a1") == 1
        # registry holds the new object
        assert store.get("a1") is b
        assert store.get("a1").created_at == 300.0
