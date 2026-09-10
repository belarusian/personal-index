"""Adversarial deep tests for personal_index.content_annotations.

Contract source: module docstrings (personal_index/content_annotations.py).
This module has NO dedicated docs page (docs/annotation.md describes the
separate personal_index/annotation.py AnnotationStore, not this
AnnotationManager), so the docstrings are the contract.

DEFECT (QA-30a): AnnotationManager.add_tag desyncs the _by_tag index.
``Annotation.add_tag`` dedupes (a tag already present is a no-op), but
``AnnotationManager.add_tag`` appends the annotation id to ``_by_tag[tag]``
UNCONDITIONALLY. So ``add_tag(id, 'x')`` called twice leaves
``annotation.tags == ['x']`` (one tag) while ``get_by_tag('x')`` returns the
same annotation id TWICE. The secondary index no longer reflects the
annotation's actual tags. Pinned xfail-strict below.

DEFECT (QA-30b): AnnotationManager.delete leaves an empty _by_content bucket.
``get_stats()['by_content']`` is documented as "the number of DISTINCT content
ids that have at least one annotation". ``delete(id)`` removes the id from
``_by_content[cid]`` but leaves the (now empty) key in place, so a content id
whose last annotation was deleted still counts. ``delete_by_content_id`` (which
pops the key) does NOT have this bug, so the two documented delete paths
disagree. Pinned xfail-strict below.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.content_annotations import (
    Annotation,
    AnnotationManager,
    AnnotationType,
)


def _ann(aid: str, cid: str, text: str = "hello", **kw) -> Annotation:
    return Annotation(content_id=cid, text=text, annotation_id=aid, **kw)


# ---------------------------------------------------------------------------
# Annotation dataclass
# ---------------------------------------------------------------------------


def test_annotation_default_type_is_note():
    a = Annotation(content_id="c", text="t")
    assert a.annotation_type is AnnotationType.NOTE


def test_annotation_default_id_is_12_hex():
    a = Annotation(content_id="c", text="t")
    assert len(a.annotation_id) == 12
    assert all(ch in "0123456789abcdef" for ch in a.annotation_id)


def test_annotation_default_tags_empty_list():
    a = Annotation(content_id="c", text="t")
    assert a.tags == []


def test_annotation_add_tag_appends_new():
    a = Annotation(content_id="c", text="t")
    a.add_tag("x")
    assert a.tags == ["x"]


def test_annotation_add_tag_dedupes():
    a = Annotation(content_id="c", text="t")
    a.add_tag("x")
    a.add_tag("x")
    assert a.tags == ["x"]


def test_annotation_add_tag_sets_updated_at():
    a = Annotation(content_id="c", text="t")
    assert a.updated_at is None
    a.add_tag("x")
    assert a.updated_at is not None


def test_annotation_remove_tag_removes_present():
    a = Annotation(content_id="c", text="t", tags=["x", "y"])
    a.remove_tag("x")
    assert a.tags == ["y"]


def test_annotation_remove_tag_noop_when_absent():
    a = Annotation(content_id="c", text="t", tags=["x"])
    a.remove_tag("z")
    assert a.tags == ["x"]


def test_annotation_update_text_sets_updated_at():
    a = Annotation(content_id="c", text="old")
    a.update_text("new")
    assert a.text == "new"
    assert a.updated_at is not None


def test_annotation_to_dict_round_trip():
    a = Annotation(
        content_id="c1",
        text="hello",
        annotation_type=AnnotationType.HIGHLIGHT,
        annotation_id="a1",
        author="alice",
        tags=["x", "y"],
        position_start=0,
        position_end=5,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    b = Annotation.from_dict(a.to_dict())
    assert b.annotation_id == a.annotation_id
    assert b.content_id == a.content_id
    assert b.text == a.text
    assert b.annotation_type is AnnotationType.HIGHLIGHT
    assert b.author == a.author
    assert b.tags == a.tags
    assert b.position_start == 0
    assert b.position_end == 5
    assert b.created_at == a.created_at
    assert b.updated_at == a.updated_at


def test_annotation_from_dict_missing_optional_fields():
    b = Annotation.from_dict({"content_id": "c1"})
    assert b.content_id == "c1"
    assert b.text == ""
    assert b.annotation_type is AnnotationType.NOTE
    assert b.author == ""
    assert b.tags == []
    assert b.position_start is None
    assert b.position_end is None
    assert b.updated_at is None
    assert b.created_at  # defaulted to a timestamp


def test_annotation_from_dict_type_as_enum_passthrough():
    b = Annotation.from_dict(
        {"content_id": "c", "annotation_type": AnnotationType.FLAG}
    )
    assert b.annotation_type is AnnotationType.FLAG


# ---------------------------------------------------------------------------
# AnnotationManager.add + lookup indexes
# ---------------------------------------------------------------------------


def test_add_populates_all_indexes():
    m = AnnotationManager()
    a = _ann("a1", "c1", author="alice", tags=["x"])
    m.add(a)
    assert m.get("a1") is a
    assert [x.annotation_id for x in m.get_by_content_id("c1")] == ["a1"]
    assert [x.annotation_id for x in m.get_by_author("alice")] == ["a1"]
    assert [x.annotation_id for x in m.get_by_type(AnnotationType.NOTE)] == ["a1"]
    assert [x.annotation_id for x in m.get_by_tag("x")] == ["a1"]


def test_add_falsy_author_skips_author_index():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", author=""))
    assert m.get_by_author("") == []
    assert m.get("a1") is not None  # still stored


def test_add_multiple_same_content():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    m.add(_ann("a2", "c1"))
    assert len(m.get_by_content_id("c1")) == 2


def test_get_missing_returns_none():
    m = AnnotationManager()
    assert m.get("nope") is None


def test_get_by_content_id_missing_returns_empty():
    m = AnnotationManager()
    assert m.get_by_content_id("nope") == []


def test_get_all_returns_all():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    m.add(_ann("a2", "c2"))
    assert len(m.get_all()) == 2


def test_count_reflects_stored():
    m = AnnotationManager()
    assert m.count() == 0
    m.add(_ann("a1", "c1"))
    assert m.count() == 1


# ---------------------------------------------------------------------------
# get_recent (negative-slice guard)
# ---------------------------------------------------------------------------


def test_get_recent_negative_limit_returns_empty():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", created_at="2026-01-01T00:00:00+00:00"))
    m.add(_ann("a2", "c2", created_at="2026-01-02T00:00:00+00:00"))
    assert m.get_recent(-1) == []


def test_get_recent_zero_limit_returns_empty():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    assert m.get_recent(0) == []


def test_get_recent_positive_limit_caps():
    m = AnnotationManager()
    for i in range(5):
        m.add(_ann(f"a{i}", f"c{i}", created_at=f"2026-01-0{i+1}T00:00:00+00:00"))
    assert len(m.get_recent(3)) == 3


def test_get_recent_sorts_newest_first():
    m = AnnotationManager()
    m.add(_ann("old", "c1", created_at="2026-01-01T00:00:00+00:00"))
    m.add(_ann("new", "c2", created_at="2026-01-02T00:00:00+00:00"))
    got = [a.annotation_id for a in m.get_recent(10)]
    assert got == ["new", "old"]


def test_get_recent_more_than_available_returns_all():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    assert len(m.get_recent(100)) == 1


# ---------------------------------------------------------------------------
# update_text / add_tag / remove_tag (manager level)
# ---------------------------------------------------------------------------


def test_manager_update_text_existing():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", text="old"))
    assert m.update_text("a1", "new") is True
    assert m.get("a1").text == "new"


def test_manager_update_text_missing_returns_false():
    m = AnnotationManager()
    assert m.update_text("nope", "x") is False


def test_manager_add_tag_updates_index():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    m.add_tag("a1", "x")
    assert [a.annotation_id for a in m.get_by_tag("x")] == ["a1"]
    assert m.get("a1").tags == ["x"]


def test_manager_add_tag_missing_id_noop():
    m = AnnotationManager()
    m.add_tag("nope", "x")
    assert m.get_by_tag("x") == []


def test_manager_remove_tag_updates_index():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", tags=["x"]))
    m.remove_tag("a1", "x")
    assert m.get_by_tag("x") == []
    assert m.get("a1").tags == []


def test_manager_remove_tag_missing_id_noop():
    m = AnnotationManager()
    m.remove_tag("nope", "x")
    assert m.get_by_tag("x") == []


# ---------------------------------------------------------------------------
# DEFECT QA-30a: manager add_tag desyncs _by_tag on duplicate
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "QA-30a: AnnotationManager.add_tag appends to _by_tag unconditionally "
        "while Annotation.add_tag dedupes; a duplicate add_tag leaves the "
        "annotation with one tag but the _by_tag index with two entries, so "
        "get_by_tag returns the same id twice."
    ),
)
def test_manager_add_tag_duplicate_does_not_desync_index():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    m.add_tag("a1", "x")
    m.add_tag("a1", "x")  # duplicate
    # The annotation's own tags are deduped...
    assert m.get("a1").tags == ["x"]
    # ...so the index must reflect exactly one entry, not two.
    assert [a.annotation_id for a in m.get_by_tag("x")] == ["a1"]


# ---------------------------------------------------------------------------
# delete / delete_by_content_id
# ---------------------------------------------------------------------------


def test_delete_existing_returns_true_and_removes():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", author="alice", tags=["x"]))
    assert m.delete("a1") is True
    assert m.get("a1") is None
    assert m.get_by_content_id("c1") == []
    assert m.get_by_author("alice") == []
    assert m.get_by_tag("x") == []
    assert m.count() == 0


def test_delete_missing_returns_false():
    m = AnnotationManager()
    assert m.delete("nope") is False


def test_delete_by_content_id_returns_count():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    m.add(_ann("a2", "c1"))
    m.add(_ann("a3", "c2"))
    assert m.delete_by_content_id("c1") == 2
    assert m.get_by_content_id("c1") == []
    assert m.count() == 1


def test_delete_by_content_id_missing_returns_zero():
    m = AnnotationManager()
    assert m.delete_by_content_id("nope") == 0


# ---------------------------------------------------------------------------
# DEFECT QA-30b: delete leaves empty _by_content bucket -> get_stats wrong
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "QA-30b: get_stats()['by_content'] is documented as the number of "
        "content ids with AT LEAST ONE annotation, but delete() leaves the "
        "now-empty _by_content key in place, so a fully-deleted content id "
        "still counts. delete_by_content_id (which pops the key) does not "
        "have this bug, so the two documented delete paths disagree."
    ),
)
def test_delete_last_annotation_zeroes_by_content_stat():
    m = AnnotationManager()
    m.add(_ann("a1", "c1"))
    assert m.get_stats()["by_content"] == 1
    m.delete("a1")
    # c1 has no annotations left, so it must not count.
    assert m.get_stats()["by_content"] == 0


# ---------------------------------------------------------------------------
# search / get_stats / clear / serialize
# ---------------------------------------------------------------------------


def test_search_case_insensitive_substring():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", text="Hello World"))
    m.add(_ann("a2", "c2", text="goodbye"))
    assert [a.annotation_id for a in m.search("hello")] == ["a1"]
    assert [a.annotation_id for a in m.search("WORLD")] == ["a1"]


def test_search_no_match_returns_empty():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", text="hello"))
    assert m.search("zzz") == []


def test_search_empty_query_matches_all():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", text="hello"))
    m.add(_ann("a2", "c2", text="world"))
    assert len(m.search("")) == 2


def test_get_stats_three_keys():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", annotation_type=AnnotationType.NOTE))
    m.add(_ann("a2", "c1", annotation_type=AnnotationType.HIGHLIGHT))
    m.add(_ann("a3", "c2", annotation_type=AnnotationType.NOTE))
    stats = m.get_stats()
    assert set(stats.keys()) == {"total", "by_content", "by_type"}
    assert stats["total"] == 3
    assert stats["by_content"] == 2  # c1, c2
    assert stats["by_type"] == {"note": 2, "highlight": 1}


def test_get_stats_empty_manager():
    m = AnnotationManager()
    stats = m.get_stats()
    assert stats == {"total": 0, "by_content": 0, "by_type": {}}


def test_clear_removes_everything():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", author="alice", tags=["x"]))
    m.clear()
    assert m.count() == 0
    assert m.get_all() == []
    assert m.get_by_author("alice") == []
    assert m.get_by_tag("x") == []


def test_serialize_deserialize_round_trip():
    m = AnnotationManager()
    m.add(_ann("a1", "c1", text="hello", author="alice", tags=["x"]))
    m.add(_ann("a2", "c2", text="world", annotation_type=AnnotationType.FLAG))
    data = m.serialize()
    m2 = AnnotationManager()
    m2.deserialize(data)
    assert m2.count() == 2
    assert m2.get("a1").text == "hello"
    assert m2.get("a1").author == "alice"
    assert m2.get("a1").tags == ["x"]
    assert m2.get("a2").annotation_type is AnnotationType.FLAG
    assert [a.annotation_id for a in m2.get_by_author("alice")] == ["a1"]


def test_deserialize_clears_existing_first():
    m = AnnotationManager()
    m.add(_ann("old", "c0"))
    m.deserialize([{"content_id": "c1", "text": "new", "annotation_id": "a1"}])
    assert m.count() == 1
    assert m.get("old") is None
    assert m.get("a1") is not None


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (module not wired to a subcommand; status is the
# installed-CLI entry point)
# ---------------------------------------------------------------------------


def test_cli_status_smoke():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "status"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Personal Index Status" in proc.stdout
