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

from personal_index.content_search import SearchIndex


def _idx_with(items):
    idx = SearchIndex()
    for it in items:
        idx.add_item(it)
    return idx


# ---------------------------------------------------------------------------
# QA-42 (RECONCILED, cycle 342): present-None id now falls back to id(item)
# and stays DISTINCT. The fix (cb6eaf0, QA-42 CLOSED cycle 300) is ON main:
#     item_id = str(item["id"]) if item.get("id") is not None else str(id(item))
# The prior xfail-strict pin documented the OLD str()-collapse defect; it is
# now a HARD PASS pinning the corrected contract (docs/content-search.md:
# "a missing/None id falls back to the object's id()"). NOTE: _build_entry
# strips the "content" key from result items, so distinctness is asserted via
# a surviving "title" marker, not via content.
# ---------------------------------------------------------------------------
def test_add_item_present_none_id_is_distinct():
    """Two items with id=None must be stored as DISTINCT items (item_count 2)."""
    idx = _idx_with(
        [
            {"id": None, "title": "marker-one", "content": "first item alpha"},
            {"id": None, "title": "marker-two", "content": "second item beta"},
        ]
    )
    # Docs: a missing/None id falls back to id(item) -> distinct keys.
    assert idx.item_count == 2, (
        "present-None ids collapsed to a shared key "
        f"(item_count={idx.item_count}, expected 2)"
    )
    # Both items must remain searchable by their unique terms, and each
    # result must be the DISTINCT item (distinguished by its title marker,
    # since _build_entry strips the "content" key).
    alpha = [e["item"].get("title") for e in idx.search("alpha")["results"]]
    beta = [e["item"].get("title") for e in idx.search("beta")["results"]]
    assert alpha == ["marker-one"], f"first item lost/wrong: {alpha}"
    assert beta == ["marker-two"], f"second item lost/wrong: {beta}"


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): mixed id shapes (present-None, absent, explicit)
# all resolve to DISTINCT keys - no cross-shape collapse.
# ---------------------------------------------------------------------------
def test_add_item_mixed_id_shapes_all_distinct():
    idx = _idx_with(
        [
            {"id": None, "title": "none-marker", "content": "alpha one"},
            {"title": "absent-marker", "content": "beta two"},
            {"id": "explicit", "title": "explicit-marker", "content": "gamma three"},
        ]
    )
    assert idx.item_count == 3, f"mixed id shapes collapsed: {idx.item_count}"
    assert [e["item"].get("title") for e in idx.search("alpha")["results"]] == ["none-marker"]
    assert [e["item"].get("title") for e in idx.search("beta")["results"]] == ["absent-marker"]
    assert [e["item"].get("title") for e in idx.search("gamma")["results"]] == ["explicit-marker"]


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): idempotence - adding the SAME dict object twice
# resolves to the same id() key, so the second add REPLACES (item_count 1),
# not a duplicate.
# ---------------------------------------------------------------------------
def test_add_item_same_object_twice_is_idempotent():
    idx = SearchIndex()
    obj = {"id": None, "title": "dup-marker", "content": "alpha text"}
    idx.add_item(obj)
    idx.add_item(obj)
    assert idx.item_count == 1, f"same-object re-add duplicated: {idx.item_count}"
    assert [e["item"].get("title") for e in idx.search("alpha")["results"]] == ["dup-marker"]


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
# Armor (cycle 342 re-probe): negative offset does not leak an all-but-last
# negative slice - it is treated as offset 0 (the page starts at the top).
# ---------------------------------------------------------------------------
def test_search_negative_offset_starts_at_top():
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one"},
            {"id": "b", "content": "beta two"},
            {"id": "c", "content": "gamma three"},
        ]
    )
    out = idx.search("one", limit=2, offset=-1)
    # total is the full match count (1 for "one"); results is the page.
    assert out["total"] == 1
    assert len(out["results"]) == 1
    assert out["results"][0]["item"].get("id") == "a"


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): unicode content is tokenized and searchable
# (lowercase + punctuation-strip must not crash on non-ASCII).
# ---------------------------------------------------------------------------
def test_search_unicode_content_is_searchable():
    idx = _idx_with(
        [
            {"id": "u1", "content": "café résumé naïve"},
            {"id": "u2", "content": "plain english text"},
        ]
    )
    out = idx.search("café")
    assert out["total"] == 1
    assert out["results"][0]["item"].get("id") == "u1"


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): a None content value degrades to empty text
# (no crash) - the item is stored but contributes no tokens.
# ---------------------------------------------------------------------------
def test_add_item_none_content_does_not_crash():
    idx = SearchIndex()
    idx.add_item({"id": "n1", "content": None})
    idx.add_item({"id": "n2", "content": "alpha text"})
    assert idx.item_count == 2
    # The None-content item is stored but not found by "alpha".
    assert [e["item"].get("id") for e in idx.search("alpha")["results"]] == ["n2"]


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): filters narrow candidates - an exact-match
# filter on a non-text field excludes non-matching items.
# ---------------------------------------------------------------------------
def test_search_filters_exact_match_narrows():
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "kind": "doc"},
            {"id": "b", "content": "alpha two", "kind": "note"},
        ]
    )
    out = idx.search("alpha", filters={"kind": "doc"})
    assert out["total"] == 1
    assert out["results"][0]["item"].get("id") == "a"


# ---------------------------------------------------------------------------
# Armor (cycle 342 re-probe): save_index/load_index round-trip preserves
# item_count and searchability (the index is lossless across a file).
# ---------------------------------------------------------------------------
def test_save_load_roundtrip_preserves_index(tmp_path):
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one"},
            {"id": "b", "content": "beta two"},
        ]
    )
    path = tmp_path / "idx.json"
    idx.save_index(str(path))
    idx2 = SearchIndex()
    idx2.load_index(str(path))
    assert idx2.item_count == 2
    assert [e["item"].get("id") for e in idx2.search("alpha")["results"]] == ["a"]
    assert [e["item"].get("id") for e in idx2.search("beta")["results"]] == ["b"]


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
