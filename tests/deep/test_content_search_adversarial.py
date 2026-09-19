"""Adversarial deep tests for personal_index.content_search.SearchIndex.

Target: the id-keying contract of SearchIndex.add_item (docs/content-search.md,
SearchIndex section):

    add_item(item) stores the item under
    `str(item.get("id", id(item)))` (a missing/`None` id falls back to the
    object's `id()`), ...

The docs promise that a *missing OR None* id falls back to the object's
`id()` so distinct items are never collapsed. The code, however, uses
`dict.get("id", id(item))`, which only applies the `id(item)` default when the
key is ABSENT — a *present* `None` value is returned as-is and stringified to
the literal `"None"`, so two `{"id": None, ...}` items collide on the single
key `"None"` and the second silently overwrites the first.

This is the 2nd public site of the id-keying str()-collapse class (1st site:
content_aggregator.merge_all, QA-41). QA-42 documents the content_search site.
"""

from __future__ import annotations

import pytest

from personal_index.content_search import SearchIndex


def _idx_with(items):
    idx = SearchIndex()
    for it in items:
        idx.add_item(it)
    return idx


# ---------------------------------------------------------------------------
# QA-42: present-None id collapses to the shared "None" key (defect, xfail)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="QA-42: SearchIndex.add_item str()-collapses present-None ids "
    "(dict.get('id', id(item)) only falls back on an ABSENT key, not a "
    "present None) - docs/content-search.md promises a distinct id() fallback "
    "for a missing/None id.",
)
def test_add_item_present_none_id_is_distinct():
    """Two items with id=None must be stored as DISTINCT items (item_count 2)."""
    idx = _idx_with(
        [
            {"id": None, "content": "first item alpha"},
            {"id": None, "content": "second item beta"},
        ]
    )
    # Docs: a missing/None id falls back to id(item) -> distinct keys.
    assert idx.item_count == 2, (
        "present-None ids collapsed to the shared 'None' key "
        f"(item_count={idx.item_count}, expected 2)"
    )
    # Both items must remain searchable by their unique terms.
    alpha = [e["item"].get("content") for e in idx.search("alpha")["results"]]
    beta = [e["item"].get("content") for e in idx.search("beta")["results"]]
    assert alpha == ["first item alpha"], f"first item lost: {alpha}"
    assert beta == ["second item beta"], f"second item lost: {beta}"


# ---------------------------------------------------------------------------
# Armor: the ABSENT-id path (key truly missing) DOES fall back to id(item)
# and stays distinct - this is the documented behavior that works.
# ---------------------------------------------------------------------------
def test_add_item_absent_id_falls_back_to_object_id_distinct():
    idx = _idx_with(
        [
            {"content": "first item alpha"},
            {"content": "second item beta"},
        ]
    )
    assert idx.item_count == 2
    # Both items survive (each unique term finds exactly one result).
    assert len(idx.search("alpha")["results"]) == 1
    assert len(idx.search("beta")["results"]) == 1


# ---------------------------------------------------------------------------
# Armor: distinct explicit ids (int vs str of the same digits) stay distinct
# in the search index (the index keys on str(id), and int 1 / str "1" both
# stringify to "1" - but here we pin that DISTINCT digit values stay distinct,
# which the index does deliver).
# ---------------------------------------------------------------------------
def test_add_item_distinct_numeric_ids_stay_distinct():
    idx = _idx_with(
        [
            {"id": 1, "content": "one alpha"},
            {"id": 2, "content": "two beta"},
        ]
    )
    assert idx.item_count == 2
    assert [e["item"].get("id") for e in idx.search("alpha")["results"]] == [1]
    assert [e["item"].get("id") for e in idx.search("beta")["results"]] == [2]


# ---------------------------------------------------------------------------
# Armor: re-add under an existing id replaces (no stale tokens survive).
# ---------------------------------------------------------------------------
def test_add_item_readd_same_id_replaces_no_stale_tokens():
    idx = SearchIndex()
    idx.add_item({"id": "x", "content": "old quantum text"})
    idx.add_item({"id": "x", "content": "new gamma text"})
    assert idx.item_count == 1
    # Old term must be gone from the index (no stale postings).
    assert "quantum" not in idx._index
    # New term is found, and the surviving item is the re-added one (id "x").
    assert [e["item"].get("id") for e in idx.search("gamma")["results"]] == ["x"]


# ---------------------------------------------------------------------------
# Armor: remove_item is a no-op for an unknown id (guard path).
# ---------------------------------------------------------------------------
def test_remove_item_unknown_id_is_noop():
    idx = _idx_with([{"id": "a", "content": "alpha text"}])
    idx.remove_item("does-not-exist")
    assert idx.item_count == 1
    assert [e["item"].get("id") for e in idx.search("alpha")["results"]] == ["a"]


# ---------------------------------------------------------------------------
# Armor: search guard path - a query that tokenizes to nothing returns the
# exact documented empty shape without touching the index.
# ---------------------------------------------------------------------------
def test_search_empty_token_query_returns_exact_empty_shape():
    idx = _idx_with([{"id": "a", "content": "alpha text"}])
    # "the" is a stop-word -> no tokens remain.
    out = idx.search("the")
    assert out == {"results": [], "total": 0, "query": "the"}


# ---------------------------------------------------------------------------
# Armor: get_suggestions guard path - limit <= 0 returns [] (negative included).
# ---------------------------------------------------------------------------
def test_get_suggestions_nonpositive_limit_returns_empty():
    idx = _idx_with(
        [{"id": i, "content": t + " word"} for i, t in enumerate(
            ["alpha", "beta", "gamma", "delta"]
        )]
    )
    assert idx.get_suggestions("a", limit=0) == []
    assert idx.get_suggestions("a", limit=-1) == []
    assert idx.get_suggestions("a", limit=5) == ["alpha"]


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed CLI, search command, empty-index guard path).
# content_search.SearchIndex is app-level (not CLI-wired); the CLI `search`
# command exercises the db-backed index.SearchIndex. This satisfies the
# per-cycle end-to-end CLI requirement.
# ---------------------------------------------------------------------------
def test_cli_search_end_to_end_empty_index_guard(tmp_path):
    import subprocess
    import sys

    data_dir = tmp_path / "e2e_qa42"
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "search", "anything",
         "--data-dir", str(data_dir)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"CLI exited {proc.returncode}: {proc.stderr}"
    assert "No indexed content found" in proc.stdout
