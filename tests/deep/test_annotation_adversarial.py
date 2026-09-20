"""Adversarial deep tests for the annotation module (cycle 307).

Tests edge cases: None/empty/whitespace inputs, unicode, duplicate IDs,
upsert reconciliation, round-trips, idempotence, property checks,
and search edge cases.
"""

import time
import pytest
from personal_index.annotation import (
    Annotation,
    AnnotationStore,
    AnnotationType,
)


# --- Annotation dataclass edge cases ---

def test_annotation_empty_strings():
    """Empty strings for all string fields should be valid."""
    a = Annotation(annotation_id="", url="", annotation_type=AnnotationType.NOTE)
    assert a.annotation_id == ""
    assert a.url == ""
    assert a.author == ""


def test_annotation_whitespace_values():
    """Whitespace-only values should be preserved."""
    a = Annotation(
        annotation_id="  ",
        url="   ",
        annotation_type=AnnotationType.NOTE,
        value="  ",
        author="  ",
    )
    assert a.annotation_id == "  "
    assert a.url == "   "
    assert a.value == "  "


def test_annotation_unicode():
    """Unicode in all string fields should be preserved."""
    a = Annotation(
        annotation_id="id-日本語-🚀",
        url="https://example.com/日本語",
        annotation_type=AnnotationType.NOTE,
        value="Note in 中文 and العربية",
        author="Üser",
    )
    assert a.annotation_id == "id-日本語-🚀"
    assert a.url == "https://example.com/日本語"
    assert a.value == "Note in 中文 and العربية"


def test_annotation_none_value():
    """None as value should be valid."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    assert a.value is None


def test_annotation_non_string_value():
    """Non-string values (int, list, dict) should be valid."""
    a1 = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.RATING, value=5)
    a2 = Annotation(annotation_id="n2", url="https://x.com", annotation_type=AnnotationType.NOTE, value=[1, 2, 3])
    a3 = Annotation(annotation_id="n3", url="https://x.com", annotation_type=AnnotationType.NOTE, value={"key": "val"})
    assert a1.value == 5
    assert a2.value == [1, 2, 3]
    assert a3.value == {"key": "val"}


def test_annotation_negative_timestamp():
    """Negative timestamps should be accepted (no validation)."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, created_at=-1.0)
    assert a.created_at == -1.0


# --- Annotation.update edge cases ---

def test_annotation_update_none_value():
    """update(value=None) should not change the value."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, value="original")
    a.update(value=None)
    assert a.value == "original"


def test_annotation_update_none_metadata():
    """update(metadata=None) should not change metadata."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, metadata={"k": "v"})
    a.update(metadata=None)
    assert a.metadata == {"k": "v"}


def test_annotation_update_both_none():
    """update() with no args should only update updated_at."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, value="v", metadata={"k": "v"})
    a.update()
    assert a.value == "v"
    assert a.metadata == {"k": "v"}
    assert a.updated_at is not None


def test_annotation_update_metadata_merge():
    """update(metadata={...}) should merge, not replace."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, metadata={"k1": "v1"})
    a.update(metadata={"k2": "v2"})
    assert a.metadata == {"k1": "v1", "k2": "v2"}


# --- Annotation.to_dict round-trip ---

def test_annotation_to_dict_roundtrip():
    """to_dict should serialize all fields."""
    a = Annotation(
        annotation_id="n1",
        url="https://example.com",
        annotation_type=AnnotationType.HIGHLIGHT,
        value="highlighted text",
        metadata={"color": "yellow"},
        author="alice",
    )
    d = a.to_dict()
    assert d["annotation_id"] == "n1"
    assert d["url"] == "https://example.com"
    assert d["type"] == "highlight"
    assert d["value"] == "highlighted text"
    assert d["metadata"] == {"color": "yellow"}
    assert d["author"] == "alice"
    assert "created_at" in d
    assert "updated_at" in d


def test_annotation_to_dict_none_value():
    """to_dict with None value should serialize correctly."""
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    d = a.to_dict()
    assert d["value"] is None
    assert d["updated_at"] is None


# --- AnnotationStore edge cases ---

def test_store_add_duplicate_id_same_url():
    """Adding same ID with same URL should not duplicate in URL index."""
    store = AnnotationStore()
    a1 = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    store.add(a1)
    a2 = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE, value="updated")
    store.add(a2)
    by_url = store.get_by_url("https://x.com")
    assert len(by_url) == 1
    assert by_url[0].value == "updated"


def test_store_add_duplicate_id_different_url():
    """Adding same ID with different URL should move it (upsert reconciliation)."""
    store = AnnotationStore()
    a1 = Annotation(annotation_id="n1", url="https://old.com", annotation_type=AnnotationType.NOTE)
    store.add(a1)
    a2 = Annotation(annotation_id="n1", url="https://new.com", annotation_type=AnnotationType.NOTE)
    store.add(a2)
    # Old URL should have no annotations
    assert store.get_by_url("https://old.com") == []
    # New URL should have the annotation
    by_url = store.get_by_url("https://new.com")
    assert len(by_url) == 1
    assert by_url[0].url == "https://new.com"


def test_store_get_nonexistent():
    """get() for nonexistent ID should return None."""
    store = AnnotationStore()
    assert store.get("nonexistent") is None


def test_store_get_by_url_nonexistent():
    """get_by_url() for URL with no annotations should return empty list."""
    store = AnnotationStore()
    assert store.get_by_url("https://no-annotations.com") == []


def test_store_get_by_type_nonexistent():
    """get_by_type() for type with no annotations should return empty list."""
    store = AnnotationStore()
    assert store.get_by_type(AnnotationType.HIGHLIGHT) == []


def test_store_update_nonexistent():
    """update() for nonexistent ID should return False."""
    store = AnnotationStore()
    assert store.update("nonexistent", value="new") is False


def test_store_remove_nonexistent():
    """remove() for nonexistent ID should return False."""
    store = AnnotationStore()
    assert store.remove("nonexistent") is False


def test_store_remove_by_url_nonexistent():
    """remove_by_url() for URL with no annotations should return 0."""
    store = AnnotationStore()
    assert store.remove_by_url("https://no-annotations.com") == 0


def test_store_remove_idempotent():
    """Removing the same ID twice should not error."""
    store = AnnotationStore()
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    store.add(a)
    assert store.remove("n1") is True
    assert store.remove("n1") is False


def test_store_remove_by_url_idempotent():
    """Removing annotations for same URL twice should not error."""
    store = AnnotationStore()
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    store.add(a)
    assert store.remove_by_url("https://x.com") == 1
    assert store.remove_by_url("https://x.com") == 0


def test_store_search_empty_query():
    """search('') should match all annotations (empty string is substring of all)."""
    store = AnnotationStore()
    a1 = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    a2 = Annotation(annotation_id="n2", url="https://y.com", annotation_type=AnnotationType.NOTE)
    store.add(a1)
    store.add(a2)
    results = store.search("")
    assert len(results) == 2


def test_store_search_case_insensitive():
    """search() should be case-insensitive."""
    store = AnnotationStore()
    a = Annotation(annotation_id="n1", url="https://Example.COM", annotation_type=AnnotationType.NOTE)
    store.add(a)
    results = store.search("example.com")
    assert len(results) == 1


def test_store_search_value_non_string():
    """search() with non-string value should not crash."""
    store = AnnotationStore()
    a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.RATING, value=5)
    store.add(a)
    results = store.search("x.com")
    assert len(results) == 1


def test_store_count_empty():
    """count should be 0 for empty store."""
    store = AnnotationStore()
    assert store.count == 0


def test_store_stats_empty():
    """get_stats() on empty store should return correct structure."""
    store = AnnotationStore()
    stats = store.get_stats()
    assert stats["total"] == 0
    assert stats["by_type"] == {}
    assert stats["urls_annotated"] == 0


def test_store_stats_after_operations():
    """get_stats() should reflect add/remove operations."""
    store = AnnotationStore()
    a1 = Annotation(annotation_id="n1", url="https://x.com", annotation_type=AnnotationType.NOTE)
    a2 = Annotation(annotation_id="n2", url="https://x.com", annotation_type=AnnotationType.HIGHLIGHT)
    store.add(a1)
    store.add(a2)
    stats = store.get_stats()
    assert stats["total"] == 2
    assert stats["by_type"]["note"] == 1
    assert stats["by_type"]["highlight"] == 1
    assert stats["urls_annotated"] == 1

    store.remove("n1")
    stats = store.get_stats()
    assert stats["total"] == 1
    assert "note" not in stats["by_type"]
    assert stats["urls_annotated"] == 1


def test_store_many_annotations():
    """Store should handle many annotations without degradation."""
    store = AnnotationStore()
    for i in range(1000):
        a = Annotation(annotation_id=f"n{i}", url=f"https://example{i}.com", annotation_type=AnnotationType.NOTE)
        store.add(a)
    assert store.count == 1000


def test_store_annotation_type_enum_values():
    """All AnnotationType enum values should be valid."""
    for t in AnnotationType:
        a = Annotation(annotation_id="n1", url="https://x.com", annotation_type=t)
        store = AnnotationStore()
        store.add(a)
        assert store.get("n1").annotation_type == t
