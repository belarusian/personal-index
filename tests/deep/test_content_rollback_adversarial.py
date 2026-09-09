"""Adversarial deep tests for personal_index.content_rollback.

Cycle 180 (VALIDATOR).

PROBE the module with adversarial inputs (None/empty/whitespace/unicode/
duplicate/out-of-range), round-trips, idempotence, property checks, and one
end-to-end CLI run.

The module's contract is documented in docs/content-rollback.md. The primary
documented hole (ARCH-47: in-memory-only persistence, no save/load) is a
design constraint, not a runtime defect, so it is NOT pinned here. The
secondary notes (rollback index semantics, name-vs-body over-promise,
create_rollback_point stores by reference, no retention cap) are all
documented and are pinned here as armor to keep them true.

No new defect was found: every adversarial input behaves exactly as the
documented contract states.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from personal_index.content_rollback import ContentRollback, RollbackPoint


# ---------------------------------------------------------------------------
# RollbackPoint dataclass
# ---------------------------------------------------------------------------


def test_rollback_point_defaults():
    p = RollbackPoint(url="u", content="c")
    assert p.url == "u"
    assert p.content == "c"
    assert p.title == ""
    assert p.timestamp == ""
    assert p.metadata == {}


def test_rollback_point_metadata_is_fresh_per_instance():
    """field(default_factory=dict) -> no shared mutable default."""
    a = RollbackPoint(url="a", content="c")
    b = RollbackPoint(url="b", content="c")
    a.metadata["k"] = 1
    assert b.metadata == {}
    assert a.metadata is not b.metadata


def test_rollback_point_timestamp_preserved_verbatim():
    p = RollbackPoint(url="u", content="c", timestamp="not-a-date")
    assert p.timestamp == "not-a-date"


def test_rollback_point_unicode_fields():
    p = RollbackPoint(url="https://例え.jp/パス", content="内容", title="タイトル")
    assert p.url == "https://例え.jp/パス"
    assert p.content == "内容"
    assert p.title == "タイトル"


def test_rollback_point_empty_url_and_content():
    p = RollbackPoint(url="", content="")
    assert p.url == ""
    assert p.content == ""


# ---------------------------------------------------------------------------
# create_rollback_point
# ---------------------------------------------------------------------------


def test_create_single_point():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    assert len(c.get_rollback_points("a")) == 1


def test_create_multiple_points_preserves_order():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    c.create_rollback_point(RollbackPoint(url="a", content="v3"))
    pts = c.get_rollback_points("a")
    assert [p.content for p in pts] == ["v1", "v2", "v3"]


def test_create_is_idempotent_in_count():
    """Calling create with the same point object twice appends twice (no dedup)."""
    c = ContentRollback()
    p = RollbackPoint(url="a", content="v1")
    c.create_rollback_point(p)
    c.create_rollback_point(p)
    assert len(c.get_rollback_points("a")) == 2


def test_create_stores_by_reference_documented_aliasing():
    """Documented secondary note: the point is stored by reference, so a
    post-creation mutation mutates the stored snapshot."""
    c = ContentRollback()
    p = RollbackPoint(url="a", content="v1")
    c.create_rollback_point(p)
    p.content = "MUTATED"
    assert c.rollback("a", 0).content == "MUTATED"


def test_create_empty_url_key():
    """url='' is a legitimate dict key (falsy but a valid key)."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="", content="emptykey"))
    assert [p.content for p in c.get_rollback_points("")] == ["emptykey"]


def test_create_unicode_url_key():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="https://例え.jp", content="c"))
    assert len(c.get_rollback_points("https://例え.jp")) == 1


def test_create_whitespace_url_key():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="   ", content="ws"))
    assert [p.content for p in c.get_rollback_points("   ")] == ["ws"]


# ---------------------------------------------------------------------------
# get_rollback_points
# ---------------------------------------------------------------------------


def test_get_rollback_points_empty_store():
    c = ContentRollback()
    assert c.get_rollback_points("missing") == []


def test_get_rollback_points_returns_shallow_copy_of_list():
    """The list is copied; appending to the result does not mutate the store."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    lst = c.get_rollback_points("a")
    lst.append(RollbackPoint(url="a", content="x"))
    assert len(c.get_rollback_points("a")) == 1


def test_get_rollback_points_shares_elements_by_reference():
    """Documented: list copied but RollbackPoint elements shared."""
    c = ContentRollback()
    p = RollbackPoint(url="a", content="v1")
    c.create_rollback_point(p)
    lst = c.get_rollback_points("a")
    assert lst[0] is p


def test_get_rollback_points_order_is_creation_order():
    c = ContentRollback()
    for i in range(5):
        c.create_rollback_point(RollbackPoint(url="a", content=f"v{i}"))
    assert [p.content for p in c.get_rollback_points("a")] == [
        "v0", "v1", "v2", "v3", "v4",
    ]


def test_get_rollback_points_does_not_mutate_store_on_read():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    c.get_rollback_points("a")
    c.get_rollback_points("a")
    assert len(c.get_rollback_points("a")) == 2


# ---------------------------------------------------------------------------
# rollback (pure accessor)
# ---------------------------------------------------------------------------


def test_rollback_default_index_is_oldest():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    assert c.rollback("a").content == "v1"


def test_rollback_index_zero_is_oldest():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    assert c.rollback("a", 0).content == "v1"


def test_rollback_negative_index_selects_from_newest():
    """Documented: index=-1 returns the newest point."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    c.create_rollback_point(RollbackPoint(url="a", content="v3"))
    assert c.rollback("a", -1).content == "v3"
    assert c.rollback("a", -2).content == "v2"


def test_rollback_out_of_range_positive_raises_indexerror():
    """Documented: index >= len(points) raises IndexError (no clamp/None)."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    with pytest.raises(IndexError):
        c.rollback("a", 5)


def test_rollback_out_of_range_negative_raises_indexerror():
    """Documented: negative magnitude exceeding list length raises IndexError."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    with pytest.raises(IndexError):
        c.rollback("a", -2)


def test_rollback_empty_url_returns_none():
    c = ContentRollback()
    assert c.rollback("missing") is None


def test_rollback_empty_url_with_index_returns_none():
    c = ContentRollback()
    assert c.rollback("missing", 3) is None


def test_rollback_is_pure_accessor_no_mutation():
    """Documented: rollback does not mutate the stored points."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    c.rollback("a", 0)
    c.rollback("a", 1)
    c.rollback("a", -1)
    assert [p.content for p in c.get_rollback_points("a")] == ["v1", "v2"]


def test_rollback_returns_same_object_as_stored():
    c = ContentRollback()
    p = RollbackPoint(url="a", content="v1")
    c.create_rollback_point(p)
    assert c.rollback("a", 0) is p


def test_rollback_single_point_index_zero():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="only"))
    assert c.rollback("a", 0).content == "only"


def test_rollback_empty_url_key():
    """url='' is a valid key; rollback('') returns its point (not None)."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="", content="emptykey"))
    assert c.rollback("").content == "emptykey"


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_single_url():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="b", content="v2"))
    c.clear("a")
    assert c.get_rollback_points("a") == []
    assert [p.content for p in c.get_rollback_points("b")] == ["v2"]


def test_clear_absent_url_is_noop():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.clear("missing")  # no exception
    assert [p.content for p in c.get_rollback_points("a")] == ["v1"]


def test_clear_falsy_none_clears_all():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.create_rollback_point(RollbackPoint(url="b", content="v2"))
    c.clear(None)
    assert c.get_rollback_points("a") == []
    assert c.get_rollback_points("b") == []


def test_clear_falsy_empty_string_clears_all():
    """Documented: url='' is falsy -> clears ALL urls, not just the '' key."""
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="", content="emptykey"))
    c.create_rollback_point(RollbackPoint(url="a", content="a1"))
    c.clear("")
    assert c.get_rollback_points("") == []
    assert c.get_rollback_points("a") == []


def test_clear_is_idempotent():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.clear("a")
    c.clear("a")  # second clear is a no-op, no exception
    assert c.get_rollback_points("a") == []


def test_clear_returns_none():
    c = ContentRollback()
    assert c.clear("a") is None
    assert c.clear(None) is None


def test_clear_all_then_create_fresh():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="v1"))
    c.clear(None)
    c.create_rollback_point(RollbackPoint(url="a", content="v2"))
    assert [p.content for p in c.get_rollback_points("a")] == ["v2"]


# ---------------------------------------------------------------------------
# Cross-method properties / round-trips
# ---------------------------------------------------------------------------


def test_property_create_then_rollback_roundtrip():
    c = ContentRollback()
    for i in range(10):
        c.create_rollback_point(RollbackPoint(url="a", content=f"v{i}"))
    for i in range(10):
        assert c.rollback("a", i).content == f"v{i}"


def test_property_multiple_urls_independent():
    c = ContentRollback()
    c.create_rollback_point(RollbackPoint(url="a", content="a1"))
    c.create_rollback_point(RollbackPoint(url="b", content="b1"))
    c.create_rollback_point(RollbackPoint(url="a", content="a2"))
    assert [p.content for p in c.get_rollback_points("a")] == ["a1", "a2"]
    assert [p.content for p in c.get_rollback_points("b")] == ["b1"]
    c.clear("a")
    assert c.get_rollback_points("a") == []
    assert [p.content for p in c.get_rollback_points("b")] == ["b1"]


def test_property_unicode_roundtrip():
    c = ContentRollback()
    c.create_rollback_point(
        RollbackPoint(url="https://例え.jp/パス", content="内容", title="タイトル")
    )
    p = c.rollback("https://例え.jp/パス", 0)
    assert p.content == "内容"
    assert p.title == "タイトル"


def test_property_boundary_large_index():
    c = ContentRollback()
    for i in range(100):
        c.create_rollback_point(RollbackPoint(url="a", content=f"v{i}"))
    assert c.rollback("a", 99).content == "v99"
    assert c.rollback("a", -100).content == "v0"
    with pytest.raises(IndexError):
        c.rollback("a", 100)


def test_in_memory_only_no_persistence_methods():
    """ARCH-47 documented design constraint: no save/load on the engine."""
    assert not hasattr(ContentRollback, "save")
    assert not hasattr(ContentRollback, "load")
    c = ContentRollback()
    assert not hasattr(c, "save")
    assert not hasattr(c, "load")


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (installed CLI boots)
# ---------------------------------------------------------------------------


def test_cli_end_to_end_version():
    result = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "--version"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
