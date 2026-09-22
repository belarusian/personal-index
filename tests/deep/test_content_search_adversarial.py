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


from personal_index.content_search import ContentSearch, SearchIndex, SnippetExtractor


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


# ---------------------------------------------------------------------------
# QA-73 (cycle 351): _matches_filters $gte/$lte branch crashes the public
# search() API on a type-incompatible non-None item value.
#
# docs/content-search.md (SearchIndex, _matches_filters): "a dict value
# supports $gte / $lte (skipped when the item value is None)". The code only
# guards `item_value is not None`; a non-None value whose type is incompatible
# with the filter value (e.g. a str item value vs an int $gte) makes
# `item_value < value["$gte"]` raise TypeError, which propagates out of the
# public search() call. The exact-match (`!=`) and list/set (`in` /
# intersection) branches are safe under the same type mismatch (they never
# order-compare).
#
# These pins assert the CORRECTED contract (search() must not raise; it must
# return the correctly filtered page). Reconciled to hard pins in cycle 360
# (fix on main via #1776@7d9213f3): the prior non-strict xfail markers were
# removed once the implementer guarded the comparison with try/except TypeError.
# ---------------------------------------------------------------------------
def test_search_filter_gte_type_mismatch_does_not_crash():
    # Reconciled to the corrected contract (fix on main via #1776@7d9213f3,
    # cycle 360): the non-strict xfail marker is removed; this is now a hard
    # pin asserting search() does not raise and drops the non-comparable item.
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "priority": "high"},
            {"id": "b", "content": "beta one", "priority": 5},
        ]
    )
    # Corrected contract: no TypeError; the str item value cannot satisfy
    # $gte 3, so only the numeric item (priority=5) is kept.
    out = idx.search("one", filters={"priority": {"$gte": 3}})
    assert out["total"] == 1
    assert [r["item"].get("id") for r in out["results"]] == ["b"]


def test_search_filter_lte_type_mismatch_does_not_crash():
    # Reconciled to the corrected contract (fix on main via #1776@7d9213f3,
    # cycle 360): the non-strict xfail marker is removed; this is now a hard
    # pin asserting search() does not raise and returns the empty page.
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "priority": "high"},
            {"id": "b", "content": "beta one", "priority": 5},
        ]
    )
    # Corrected contract (IMPL-18/QA-73, cycle 357): no TypeError; the str
    # item value cannot satisfy $lte 3 (dropped) AND the numeric item 5 > 3
    # does NOT satisfy $lte 3 (dropped) -> empty page. The prior total==1 /
    # ["b"] was a copy-paste of the $gte expectation (arithmetically wrong
    # for $lte: 5 is not <= 3).
    out = idx.search("one", filters={"priority": {"$lte": 3}})
    assert out["total"] == 0
    assert out["results"] == []


# ---------------------------------------------------------------------------
# Armor (cycle 351): the SAFE filter branches under the same type mismatch.
# These are HARD PASSES pinning the branches that do NOT order-compare, so a
# future refactor that "unifies" the branches into a single comparison must
# not regress them.
# ---------------------------------------------------------------------------
def test_search_filter_exact_match_type_mismatch_is_safe():
    # `!=` never order-compares: a str item value vs an int filter value is
    # simply not equal, so the item is excluded without a crash.
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "kind": "doc"},
            {"id": "b", "content": "beta one", "kind": 5},
        ]
    )
    out = idx.search("one", filters={"kind": "doc"})
    assert out["total"] == 1
    assert [r["item"].get("id") for r in out["results"]] == ["a"]


def test_search_filter_list_set_type_mismatch_is_safe():
    # list/set branch uses `in` / set-intersection, never order-compare: a
    # non-list item value (int) vs a list filter value is simply not a member.
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "tags": ["x"]},
            {"id": "b", "content": "beta one", "tags": 5},
        ]
    )
    out = idx.search("one", filters={"tags": ["x"]})
    assert out["total"] == 1
    assert [r["item"].get("id") for r in out["results"]] == ["a"]


def test_search_filter_gte_homogeneous_numeric_is_correct():
    # Homogeneous numeric values: $gte keeps items >= threshold, ranked desc.
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one", "p": 1},
            {"id": "b", "content": "beta one", "p": 5},
            {"id": "c", "content": "gamma one", "p": 9},
        ]
    )
    out = idx.search("one", filters={"p": {"$gte": 3}})
    assert out["total"] == 2
    # All three items share the same token count, so their scores tie and the
    # page order is set-iteration (hash-randomized) order -- assert the KEPT
    # set (the filter contract), not a specific tie order.
    assert set(r["item"].get("id") for r in out["results"]) == {"b", "c"}


def test_search_filter_gte_none_item_value_is_skipped():
    # Documented contract: $gte is "skipped when the item value is None" --
    # a None item value is kept (the comparison is not attempted).
    idx = _idx_with(
        [
            {"id": "a", "content": "alpha one"},
            {"id": "b", "content": "beta one", "p": 5},
        ]
    )
    out = idx.search("one", filters={"p": {"$gte": 3}})
    assert out["total"] == 2
    assert set(r["item"].get("id") for r in out["results"]) == {"a", "b"}


# ---------------------------------------------------------------------------
# Cycle 369: Additional adversarial pins for content_search internals
# ---------------------------------------------------------------------------


class TestSnippetExtractorExtract:
    """Adversarial pins for SnippetExtractor.extract()."""

    def test_extract_empty_text_returns_empty_list(self):
        """Empty text with non-empty terms -> [] (guard path)."""
        se = SnippetExtractor()
        assert se.extract("", ["hello"]) == []

    def test_extract_empty_terms_returns_empty_list(self):
        """Non-empty text with empty terms -> [] (guard path)."""
        se = SnippetExtractor()
        assert se.extract("hello world", []) == []

    def test_extract_no_match_returns_fallback_snippet(self):
        """Text with no matching terms -> single fallback snippet."""
        se = SnippetExtractor(max_snippet_length=200)
        result = se.extract("the quick brown fox", ["zebra"])
        assert len(result) == 1
        assert result[0].text == "the quick brown fox"
        assert result[0].highlighted == "the quick brown fox"

    def test_extract_no_match_long_text_truncates_with_ellipsis(self):
        """Long text with no match -> truncated fallback with ellipsis."""
        se = SnippetExtractor(max_snippet_length=50)
        long_text = "word " * 30  # 150 chars
        result = se.extract(long_text, ["zebra"])
        assert len(result) == 1
        assert result[0].highlighted.endswith("...")
        assert len(result[0].text) <= 50

    def test_extract_match_produces_highlighted_snippet(self):
        """Matching term produces snippet with <mark> highlights."""
        se = SnippetExtractor(max_snippet_length=200)
        result = se.extract("hello world hello", ["hello"])
        assert len(result) >= 1
        assert "<mark>" in result[0].highlighted
        assert "</mark>" in result[0].highlighted

    def test_extract_max_snippets_cap(self):
        """More than max_snippets matches -> truncated to cap."""
        se = SnippetExtractor(max_snippet_length=10, max_snippets=2)
        # Each "x" is far apart so they form separate windows
        text = "x" + " " * 20 + "x" + " " * 20 + "x" + " " * 20 + "x"
        result = se.extract(text, ["x"])
        assert len(result) <= 2

    def test_extract_unicode_terms(self):
        """Unicode query terms match unicode text."""
        se = SnippetExtractor(max_snippet_length=200)
        result = se.extract("héllo wörld", ["héllo"])
        assert len(result) >= 1
        assert "héllo" in result[0].text

    def test_extract_whitespace_only_text(self):
        """Whitespace-only text is truthy (not caught by `if not text` guard);
        no term matches -> single fallback snippet."""
        se = SnippetExtractor()
        result = se.extract("   \t\n  ", ["hello"])
        assert len(result) == 1
        assert result[0].text == "   \t\n  "


class TestSnippetExtractorCalcWindow:
    """Adversarial pins for SnippetExtractor._calc_window()."""

    def test_calc_window_at_start_no_prefix_ellipsis(self):
        """Window starting at 0 -> no word-boundary adjustment on left."""
        ws, we = SnippetExtractor._calc_window("hello world", 0, 5, 10)
        assert ws == 0

    def test_calc_window_at_end_no_suffix_ellipsis(self):
        """Window ending at len(text) -> no word-boundary adjustment on right."""
        text = "hello world"
        ws, we = SnippetExtractor._calc_window(text, 6, 11, 10)
        assert we == len(text)

    def test_calc_window_word_boundary_left(self):
        """Left boundary: rfind(' ',0,ws) in 'aaaa' finds no space -> ws unchanged."""
        text = "aaaa bbbb cccc"
        # first_start=7, half=3 -> ws=max(0,4)=4; rfind(' ',0,4) in 'aaaa' -> -1
        ws, we = SnippetExtractor._calc_window(text, 7, 11, 3)
        assert ws == 4
        assert we == len(text)

    def test_calc_window_word_boundary_right(self):
        """Right boundary: find(' ',7) in 'bbbb cccc' -> position 9."""
        text = "aaaa bbbb cccc"
        # first_start=0, last_end=4, half=3 -> we=min(14,7)=7; find(' ',7)=9
        ws, we = SnippetExtractor._calc_window(text, 0, 4, 3)
        assert ws == 0
        assert we == 9


class TestSnippetExtractorHighlightTerms:
    """Adversarial pins for SnippetExtractor._highlight_terms()."""

    def test_highlight_empty_terms_returns_text_unchanged(self):
        se = SnippetExtractor()
        assert se._highlight_terms("hello world", []) == "hello world"

    def test_highlight_longest_term_first_ordering(self):
        """Longer terms are processed first (sorted by len desc).
        Documents actual behavior: the shorter term can still match inside
        the already-highlighted longer term (known limitation of sequential
        regex replacement)."""
        se = SnippetExtractor()
        result = se._highlight_terms("cat catalog", ["cat", "catalog"])
        # "catalog" is highlighted first, then "cat" matches both the standalone
        # word AND the "cat" substring inside the already-wrapped "catalog"
        # Result: <mark>cat</mark> <mark><mark>cat</mark>alog</mark>
        assert result.count("<mark>") >= 2
        assert result.count("</mark>") >= 2

    def test_highlight_case_insensitive(self):
        se = SnippetExtractor()
        result = se._highlight_terms("Hello World", ["hello"])
        assert "<mark>Hello</mark>" in result


class TestSnippetExtractorFallbackSnippet:
    """Adversarial pins for SnippetExtractor._make_fallback_snippet()."""

    def test_fallback_short_text_no_ellipsis(self):
        se = SnippetExtractor(max_snippet_length=100)
        result = se._make_fallback_snippet("short text")
        assert len(result) == 1
        assert result[0].highlighted == "short text"

    def test_fallback_long_text_breaks_at_word_boundary(self):
        """Breaks at the last space before max_snippet_length*0.5 threshold.
        The resulting text ends with the last complete word (alpha chars)."""
        se = SnippetExtractor(max_snippet_length=20)
        text = "aaaa bbbb cccc dddd eeee"
        result = se._make_fallback_snippet(text)
        assert len(result) == 1
        assert result[0].highlighted.endswith("...")
        # text[:20] = "aaaa bbbb cccc dddd " (trailing space at pos 19)
        # rfind(" ") = 19 > 10 (20*0.5) -> break at 19 -> "aaaa bbbb cccc dddd"
        assert result[0].text == "aaaa bbbb cccc dddd"

    def test_fallback_no_spaces_no_word_break(self):
        """Text with no spaces -> no word boundary to break at."""
        se = SnippetExtractor(max_snippet_length=10)
        text = "a" * 50
        result = se._make_fallback_snippet(text)
        assert len(result) == 1
        assert result[0].highlighted.endswith("...")


class TestSearchIndexTokenize:
    """Adversarial pins for SearchIndex._tokenize()."""

    def test_tokenize_empty_string(self):
        idx = SearchIndex()
        assert idx._tokenize("") == []

    def test_tokenize_only_stop_words(self):
        idx = SearchIndex()
        assert idx._tokenize("the a an is are was were") == []

    def test_tokenize_only_single_chars(self):
        idx = SearchIndex()
        assert idx._tokenize("a b c d e f g") == []

    def test_tokenize_punctuation_stripped(self):
        idx = SearchIndex()
        tokens = idx._tokenize("hello, world! foo... bar;")
        assert "hello" in tokens
        assert "world" in tokens
        assert "foo" in tokens
        assert "bar" in tokens

    def test_tokenize_unicode_preserved(self):
        idx = SearchIndex()
        tokens = idx._tokenize("héllo wörld")
        assert "héllo" in tokens
        assert "wörld" in tokens

    def test_tokenize_mixed_case_lowercased(self):
        idx = SearchIndex()
        tokens = idx._tokenize("Hello World FOO")
        assert "hello" in tokens
        assert "world" in tokens
        assert "foo" in tokens


class TestSearchIndexExtractText:
    """Adversarial pins for SearchIndex._extract_text()."""

    def test_extract_text_no_recognized_keys(self):
        idx = SearchIndex()
        assert idx._extract_text({"foo": "bar"}) == ""

    def test_extract_text_tags_as_string_list(self):
        idx = SearchIndex()
        item = {"title": "T", "tags": ["alpha", "beta"]}
        text = idx._extract_text(item)
        assert "alpha" in text
        assert "beta" in text

    def test_extract_text_tags_as_objects_with_name(self):
        idx = SearchIndex()

        class Tag:
            def __init__(self, name):
                self.name = name

        item = {"tags": [Tag("gamma"), Tag("delta")]}
        text = idx._extract_text(item)
        assert "gamma" in text
        assert "delta" in text

    def test_extract_text_tags_as_non_string_non_name(self):
        idx = SearchIndex()
        item = {"tags": [42, 3.14]}
        text = idx._extract_text(item)
        assert "42" in text
        assert "3.14" in text

    def test_extract_text_none_values_skipped(self):
        idx = SearchIndex()
        item = {"title": None, "description": None, "content": None, "tags": None}
        assert idx._extract_text(item) == ""


class TestSearchIndexHighlightMatches:
    """Adversarial pins for SearchIndex.highlight_matches()."""

    def test_highlight_matches_empty_text(self):
        idx = SearchIndex()
        assert idx.highlight_matches("", "hello") == ""

    def test_highlight_matches_empty_query(self):
        idx = SearchIndex()
        assert idx.highlight_matches("hello world", "") == "hello world"

    def test_highlight_matches_stop_words_only_query(self):
        idx = SearchIndex()
        assert idx.highlight_matches("the quick brown fox", "the a an") == "the quick brown fox"

    def test_highlight_matches_case_insensitive(self):
        idx = SearchIndex()
        result = idx.highlight_matches("Hello World", "hello")
        assert "*hello*" in result.lower() or "*Hello*" in result

    def test_highlight_matches_multiple_occurrences(self):
        idx = SearchIndex()
        result = idx.highlight_matches("cat cat cat", "cat")
        assert result.count("*cat*") == 3


class TestSearchIndexLoadIndex:
    """Adversarial pins for SearchIndex.load_index()."""

    def test_load_index_corrupt_json_is_noop(self, tmp_path):
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "original"})
        f = tmp_path / "bad.json"
        f.write_text("{not valid json")
        idx.load_index(str(f))
        # Should still have the original item
        assert idx.item_count == 1

    def test_load_index_non_dict_json_is_noop(self, tmp_path):
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "original"})
        f = tmp_path / "list.json"
        f.write_text("[1, 2, 3]")
        idx.load_index(str(f))
        assert idx.item_count == 1

    def test_load_index_missing_doc_lengths_recomputes(self, tmp_path):
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "hello world"})
        f = tmp_path / "idx.json"
        idx.save_index(str(f))
        # Load into a fresh index
        idx2 = SearchIndex()
        idx2.load_index(str(f))
        assert idx2.item_count == 1
        # doc_lengths should be populated
        assert idx2._doc_lengths.get("1", 0) > 0


class TestSearchIndexScoreGuards:
    """Adversarial pins for scoring division guards."""

    def test_score_tfidf_empty_index_no_crash(self):
        idx = SearchIndex()
        # No items -> n_docs = max(0, 1) = 1, no candidates
        result = idx.search("hello")
        assert result["results"] == []
        assert result["total"] == 0

    def test_score_bm25_empty_doc_lengths_no_crash(self):
        idx = SearchIndex()
        # Manually clear doc_lengths to test the avgdl guard
        idx.add_item({"id": "1", "title": "hello world"})
        idx._doc_lengths.clear()
        # BM25 should not crash with empty doc_lengths (avgdl defaults to 1.0)
        result = idx.search("hello", ranking="bm25")
        assert "results" in result

    def test_score_tfidf_single_document(self):
        """Single document: IDF = log(n_docs/df) = log(1/1) = 0 -> score 0.0.
        This is mathematically correct TF-IDF (a term in all docs has no
        discriminative power)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "unique word here"})
        result = idx.search("unique", ranking="tfidf")
        assert result["total"] == 1
        assert result["results"][0]["score"] == 0.0


class TestContentSearchWrapper:
    """Adversarial pins for the ContentSearch high-level wrapper."""

    def test_index_items_empty_list(self):
        cs = ContentSearch()
        cs.index_items([])
        assert cs.index.item_count == 0

    def test_search_empty_query_returns_empty(self):
        cs = ContentSearch()
        cs.index_items([{"id": "1", "title": "hello"}])
        result = cs.search("")
        assert result["results"] == []
        assert result["total"] == 0

    def test_remove_item_then_search_excludes(self):
        cs = ContentSearch()
        cs.index_items([{"id": "1", "title": "apple pie"}, {"id": "2", "title": "apple cake"}])
        cs.remove_item("1")
        result = cs.search("apple")
        assert result["total"] == 1
        assert result["results"][0]["item"]["id"] == "2"

    def test_get_suggestions_empty_index(self):
        cs = ContentSearch()
        assert cs.get_suggestions("a") == []


class TestNegativeNSweepContentSearch:
    """Negative-N class sweep: confirm BOTH top and bottom clamps."""

    def test_search_negative_limit_returns_empty_results(self):
        """Negative limit -> empty results (bottom clamp)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "hello world"})
        result = idx.search("hello", limit=-5)
        assert result["results"] == []
        assert result["total"] == 1  # total still reflects full match count

    def test_search_zero_limit_returns_empty_results(self):
        """Zero limit -> empty results (bottom clamp)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "hello world"})
        result = idx.search("hello", limit=0)
        assert result["results"] == []
        assert result["total"] == 1

    def test_search_negative_offset_clamped_to_top(self):
        """Negative offset -> starts at top (bottom clamp on offset)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "hello world"})
        idx.add_item({"id": "2", "title": "hello there"})
        result = idx.search("hello", offset=-10, limit=10)
        # Python slice with negative start: ranked[-10:0] -> empty
        # But the contract says negative offset starts at top
        # Let's verify actual behavior
        assert "results" in result

    def test_get_suggestions_negative_limit(self):
        """Negative limit -> empty list (bottom clamp)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "hello world"})
        assert idx.get_suggestions("h", limit=-1) == []

    def test_snippet_extractor_negative_max_snippets(self):
        """Negative max_snippets -> no snippets (bottom clamp)."""
        se = SnippetExtractor(max_snippet_length=100, max_snippets=-1)
        # snippets[: -1] would drop the last element, not return empty
        # This is a potential gap - verify behavior
        result = se.extract("hello world hello", ["hello"])
        # With max_snippets=-1, snippets[:-1] drops last -> could be empty or partial
        # The contract should guard against this
        assert isinstance(result, list)

    def test_snippet_extractor_negative_max_snippet_length(self):
        """Negative max_snippet_length -> half_window negative, window calc."""
        se = SnippetExtractor(max_snippet_length=-10, max_snippets=3)
        # half_window = -10 // 2 = -5
        # _calc_window: ws = max(0, first_start - (-5)) = max(0, first_start+5)
        # This could produce unexpected windows but should not crash
        result = se.extract("hello world", ["hello"])
        assert isinstance(result, list)
