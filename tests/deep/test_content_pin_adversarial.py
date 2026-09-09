"""Adversarial deep tests for personal_index.content_pin.

Cycle 179 (VALIDATOR).

PROBE the module with adversarial inputs (None/empty/whitespace/unicode/
duplicate/out-of-range), round-trips, idempotence, property checks, and one
end-to-end CLI run.

Two real contract violations found (filed as QA-17, QA-18) are pinned here as
xfail-strict so the suite stays green while documenting the defect:

* QA-17: ``_load`` crashes with an uncaught ``AttributeError`` when a valid
  JSON file maps an id to a non-dict value (e.g. ``{"a": "notadict"}``). The
  except clause catches ``(json.JSONDecodeError, KeyError, TypeError)`` and
  resets to empty -- a defensive-load contract -- but ``AttributeError`` is
  not in the tuple.
* QA-18: ``pin`` with non-JSON-serializable metadata (e.g. a set) raises
  ``TypeError`` from ``_save`` which is NOT caught by ``except OSError``; the
  item is left pinned in-memory, violating the documented rollback contract
  ("on failure the in-memory state is rolled back so the item is not left
  pinned").
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from unittest import mock

import pytest

from personal_index.content_pin import ContentPinner, PinnedItem, pin_content, unpin_content


# ---------------------------------------------------------------------------
# PinnedItem dataclass
# ---------------------------------------------------------------------------


def test_pinned_item_default_pinned_at_set():
    item = PinnedItem(item_id="x")
    assert item.pinned_at != ""
    # ISO-8601 with timezone
    assert "T" in item.pinned_at


def test_pinned_item_explicit_pinned_at_preserved():
    item = PinnedItem(item_id="x", pinned_at="2020-01-01T00:00:00+00:00")
    assert item.pinned_at == "2020-01-01T00:00:00+00:00"


def test_pinned_item_default_metadata_is_isolated():
    a = PinnedItem(item_id="a")
    b = PinnedItem(item_id="b")
    a.metadata["k"] = "v"
    assert b.metadata == {}


# ---------------------------------------------------------------------------
# pin / unpin basics
# ---------------------------------------------------------------------------


def test_pin_returns_true_and_is_pinned(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    assert p.pin("a") is True
    assert p.is_pinned("a") is True


def test_pin_with_reason_and_metadata(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a", reason="important", metadata={"tag": "x"})
    item = p.get_pinned_items()[0]
    assert item.reason == "important"
    assert item.metadata == {"tag": "x"}


def test_pin_metadata_none_becomes_empty_dict(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a", metadata=None)
    assert p.get_pinned_items()[0].metadata == {}


def test_unpin_pinned_returns_true_and_removes(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a")
    assert p.unpin("a") is True
    assert p.is_pinned("a") is False


def test_unpin_non_pinned_returns_true(tmp_path):
    # Docstring: "True if successfully unpinned (or was not pinned)."
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    assert p.unpin("never-pinned") is True


def test_pin_idempotent_same_id_overwrites(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a", reason="first")
    p.pin("a", reason="second")
    items = p.get_pinned_items()
    assert len(items) == 1
    assert items[0].reason == "second"


def test_unpin_idempotent(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a")
    assert p.unpin("a") is True
    # second unpin of an already-unpinned item is still True (not pinned)
    assert p.unpin("a") is True


# ---------------------------------------------------------------------------
# Guard inputs: None / empty / whitespace / unicode
# ---------------------------------------------------------------------------


def test_pin_empty_string_id(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    assert p.pin("") is True
    assert p.is_pinned("") is True


def test_pin_whitespace_id(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    assert p.pin("   ") is True
    assert p.is_pinned("   ") is True


def test_pin_unicode_id(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    uid = "pín-日本語-📌"
    assert p.pin(uid) is True
    assert p.is_pinned(uid) is True


def test_pin_unicode_id_round_trip(tmp_path):
    sp = str(tmp_path / "p.json")
    p = ContentPinner(storage_path=sp)
    uid = "pín-日本語-📌"
    p.pin(uid, reason="café")
    p2 = ContentPinner(storage_path=sp)
    assert p2.is_pinned(uid) is True
    assert p2.get_pinned_items()[0].reason == "café"


def test_pin_none_id_in_memory(tmp_path):
    # pin(None) is accepted in-memory (no type guard); see QA-17 for the
    # persistence round-trip inconsistency (None -> "null" string key).
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    assert p.pin(None) is True
    assert p.is_pinned(None) is True


def test_pin_none_id_round_trip_inconsistent(tmp_path):
    # pin(None) persists as the string key "null" (JSON serializes None ->
    # null, reload reads a str key). So after reload is_pinned(None) is False
    # while in-memory it was True. Pinned as a property documenting the
    # current (inconsistent) behavior; the round-trip should be stable.
    sp = str(tmp_path / "p.json")
    p = ContentPinner(storage_path=sp)
    p.pin(None)
    p2 = ContentPinner(storage_path=sp)
    assert p2.is_pinned(None) is False
    assert p2.is_pinned("null") is True


# ---------------------------------------------------------------------------
# Ordering / stability / duplicates
# ---------------------------------------------------------------------------


def test_get_pinned_items_insertion_order(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    for x in ["a", "b", "c"]:
        p.pin(x)
    assert [i.item_id for i in p.get_pinned_items()] == ["a", "b", "c"]


def test_get_pinned_items_order_stable_across_reload(tmp_path):
    sp = str(tmp_path / "p.json")
    p = ContentPinner(storage_path=sp)
    for x in ["a", "b", "c"]:
        p.pin(x)
    p2 = ContentPinner(storage_path=sp)
    assert [i.item_id for i in p2.get_pinned_items()] == ["a", "b", "c"]


def test_get_pinned_items_returns_copy(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a")
    items = p.get_pinned_items()
    items.clear()
    assert len(p.get_pinned_items()) == 1


def test_duplicate_ids_collapse_to_one(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a")
    p.pin("a")
    p.pin("a")
    assert len(p.get_pinned_items()) == 1


# ---------------------------------------------------------------------------
# Boundary lengths
# ---------------------------------------------------------------------------


def test_pin_very_long_id(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    long_id = "x" * 10000
    assert p.pin(long_id) is True
    assert p.is_pinned(long_id) is True


def test_pin_very_long_reason_and_metadata(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "p.json"))
    p.pin("a", reason="r" * 5000, metadata={"blob": "b" * 5000})
    item = p.get_pinned_items()[0]
    assert len(item.reason) == 5000
    assert len(item.metadata["blob"]) == 5000


# ---------------------------------------------------------------------------
# Round-trip / persistence
# ---------------------------------------------------------------------------


def test_round_trip_multiple_items(tmp_path):
    sp = str(tmp_path / "p.json")
    p = ContentPinner(storage_path=sp)
    p.pin("a", reason="ra", metadata={"k": "v"})
    p.pin("b", reason="rb")
    p2 = ContentPinner(storage_path=sp)
    by_id = {i.item_id: i for i in p2.get_pinned_items()}
    assert set(by_id) == {"a", "b"}
    assert by_id["a"].reason == "ra"
    assert by_id["a"].metadata == {"k": "v"}
    assert by_id["b"].reason == "rb"


def test_metadata_int_keys_become_string_keys_on_reload(tmp_path):
    # JSON object keys are always strings; int keys round-trip as str keys.
    sp = str(tmp_path / "p.json")
    p = ContentPinner(storage_path=sp)
    p.pin("x", metadata={1: "one"})
    p2 = ContentPinner(storage_path=sp)
    assert p2.get_pinned_items()[0].metadata == {"1": "one"}


def test_storage_file_created_on_first_pin(tmp_path):
    sp = str(tmp_path / "nested" / "deep" / "p.json")
    p = ContentPinner(storage_path=sp)
    assert not os.path.exists(sp)
    p.pin("a")
    assert os.path.exists(sp)


def test_load_missing_file_yields_empty(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "absent.json"))
    assert p.get_pinned_items() == []


# ---------------------------------------------------------------------------
# Defensive load: corrupted / non-dict JSON
# ---------------------------------------------------------------------------


def test_load_corrupted_json_yields_empty(tmp_path):
    sp = str(tmp_path / "c.json")
    with open(sp, "w") as f:
        f.write("{not valid json")
    p = ContentPinner(storage_path=sp)
    assert p.get_pinned_items() == []


def test_load_non_dict_json_yields_empty(tmp_path):
    sp = str(tmp_path / "l.json")
    with open(sp, "w") as f:
        f.write("[1, 2, 3]")
    p = ContentPinner(storage_path=sp)
    assert p.get_pinned_items() == []


def test_load_empty_dict_yields_empty(tmp_path):
    sp = str(tmp_path / "e.json")
    with open(sp, "w") as f:
        f.write("{}")
    p = ContentPinner(storage_path=sp)
    assert p.get_pinned_items() == []


def test_load_missing_fields_defaults(tmp_path):
    # A stored item missing reason/metadata should load with defaults.
    sp = str(tmp_path / "d.json")
    with open(sp, "w") as f:
        json.dump({"a": {"pinned_at": "2020-01-01T00:00:00+00:00"}}, f)
    p = ContentPinner(storage_path=sp)
    item = p.get_pinned_items()[0]
    assert item.reason == ""
    assert item.metadata == {}


@pytest.mark.xfail(
    strict=True,
    reason="QA-17: _load raises uncaught AttributeError on a valid-JSON file "
    "with a non-dict value (e.g. {'a': 'notadict'}); the defensive-load "
    "contract (except json.JSONDecodeError/KeyError/TypeError -> empty) does "
    "not cover AttributeError. Should load to empty, not crash.",
)
def test_load_non_dict_value_yields_empty(tmp_path):
    sp = str(tmp_path / "s.json")
    with open(sp, "w") as f:
        json.dump({"a": "notadict"}, f)
    p = ContentPinner(storage_path=sp)
    assert p.get_pinned_items() == []


# ---------------------------------------------------------------------------
# OSError rollback contract
# ---------------------------------------------------------------------------


def test_pin_oserror_rolls_back(tmp_path):
    sp = str(tmp_path / "r.json")
    p = ContentPinner(storage_path=sp)
    p.pin("a")
    with mock.patch.object(p, "_save", side_effect=OSError("disk full")):
        assert p.pin("b") is False
    # failed pin rolled back; prior pin intact
    assert p.is_pinned("b") is False
    assert p.is_pinned("a") is True


def test_unpin_oserror_rolls_back(tmp_path):
    sp = str(tmp_path / "r.json")
    p = ContentPinner(storage_path=sp)
    p.pin("a")
    with mock.patch.object(p, "_save", side_effect=OSError("disk full")):
        assert p.unpin("a") is False
    # failed unpin rolled back; item still pinned
    assert p.is_pinned("a") is True


@pytest.mark.xfail(
    strict=True,
    reason="QA-18: pin with non-JSON-serializable metadata (a set) raises "
    "TypeError from _save which is NOT caught by 'except OSError'; the item "
    "is left pinned in-memory, violating the documented rollback contract. "
    "Should return False and roll back, not raise.",
)
def test_pin_non_serializable_metadata_rolls_back(tmp_path):
    sp = str(tmp_path / "ns.json")
    p = ContentPinner(storage_path=sp)
    p.pin("good")
    result = p.pin("bad", metadata={"a": {1, 2, 3}})
    assert result is False
    assert p.is_pinned("bad") is False
    assert p.is_pinned("good") is True


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all(tmp_path):
    sp = str(tmp_path / "cl.json")
    p = ContentPinner(storage_path=sp)
    p.pin("a")
    p.pin("b")
    p.clear()
    assert p.get_pinned_items() == []


def test_clear_persists_empty(tmp_path):
    sp = str(tmp_path / "cl.json")
    p = ContentPinner(storage_path=sp)
    p.pin("a")
    p.clear()
    p2 = ContentPinner(storage_path=sp)
    assert p2.get_pinned_items() == []


def test_clear_idempotent(tmp_path):
    p = ContentPinner(storage_path=str(tmp_path / "cl.json"))
    p.clear()
    p.clear()
    assert p.get_pinned_items() == []


# ---------------------------------------------------------------------------
# Module-level convenience functions (default pinner)
# ---------------------------------------------------------------------------


def test_pin_content_and_unpin_content_round_trip(tmp_path, monkeypatch):
    # Redirect the default pinner's storage to a temp file so we do not touch
    # the real ~/.personal_index/pinned_items.json.
    import personal_index.content_pin as cp

    monkeypatch.setattr(cp, "_default_pinner", None)
    cp._default_pinner = ContentPinner(storage_path=str(tmp_path / "def.json"))
    try:
        assert pin_content("x", reason="r") is True
        assert cp._default_pinner.is_pinned("x") is True
        assert unpin_content("x") is True
        assert cp._default_pinner.is_pinned("x") is False
    finally:
        cp._default_pinner = None


# ---------------------------------------------------------------------------
# End-to-end CLI run
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
