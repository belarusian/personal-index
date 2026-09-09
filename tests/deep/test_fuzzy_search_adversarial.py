"""Adversarial deep tests for personal_index.fuzzy_search.

Contract source: personal_index/fuzzy_search.py docstrings. These tests pin
the documented behavior against adversarial inputs:

  * levenshtein_distance - empty/identical/symmetric/unicode, non-negative,
    the classic kitten->sitting == 3, and the O(min) space swap (longer s1).
  * levenshtein_similarity - both-empty -> 1.0, one-empty -> 0.0, identical
    -> 1.0, and the [0.0, 1.0] range property across a grid.
  * FuzzyMatch.__post_init__ - matched_indices=None is normalized to [].
  * FuzzySearcher.search - empty query / empty texts guard -> [], exact match
    score 1.0, substring score 0.9, min_score boundary is inclusive (>=),
    out-of-range min_score (2.0 -> [], -1 -> everything), unicode, duplicate
    texts, whitespace-only query/text, idempotence, and sorted-descending.
  * FuzzySearcher.search_in_dict - empty dict / empty query -> [], key/value
    dedup (a key equal to a value is scored once).
  * highlight / highlight_html - empty indices -> text unchanged, exact
    escape/mark wrapping, and the query-longer-than-text best-window path.
  * search_with_highlight - plain and html round-trips.
  * one end-to-end run through the installed CLI (init + search on an empty
    index).

fuzzy_search is a standalone module (not directly wired to a CLI subcommand),
so the CLI end-to-end run exercises the installed entrypoint's guard path
rather than a fuzzy-specific command.
"""

from __future__ import annotations


from personal_index.fuzzy_search import (
    FuzzyMatch,
    FuzzySearcher,
    levenshtein_distance,
    levenshtein_similarity,
)


# --- levenshtein_distance -------------------------------------------------

def test_levenshtein_empty_empty_is_zero():
    assert levenshtein_distance("", "") == 0


def test_levenshtein_one_empty_is_length_of_other():
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3


def test_levenshtein_identical_is_zero():
    assert levenshtein_distance("kitten", "kitten") == 0


def test_levenshtein_classic_kitten_sitting_is_three():
    assert levenshtein_distance("kitten", "sitting") == 3


def test_levenshtein_is_symmetric():
    assert levenshtein_distance("abc", "xyz") == levenshtein_distance("xyz", "abc")
    assert levenshtein_distance("flaw", "lawn") == levenshtein_distance("lawn", "flaw")


def test_levenshtein_is_non_negative_property():
    for a in ["", "a", "ab", "abc", "kitten", "sitting"]:
        for b in ["", "a", "ab", "abc", "kitten", "sitting"]:
            assert levenshtein_distance(a, b) >= 0


def test_levenshtein_longer_first_argument_swaps_for_space():
    # The implementation swaps so s1 is the shorter string; result must be
    # identical to the short-first ordering.
    assert levenshtein_distance("sitting", "kitten") == levenshtein_distance("kitten", "sitting")


def test_levenshtein_unicode():
    # Cyrillic edit distance: one substitution.
    assert levenshtein_distance("привет", "привет") == 0
    assert levenshtein_distance("привет", "приветт") == 1


# --- levenshtein_similarity ----------------------------------------------

def test_similarity_both_empty_is_one():
    assert levenshtein_similarity("", "") == 1.0


def test_similarity_one_empty_is_zero():
    assert levenshtein_similarity("a", "") == 0.0
    assert levenshtein_similarity("", "a") == 0.0


def test_similarity_identical_is_one():
    assert levenshtein_similarity("kitten", "kitten") == 1.0


def test_similarity_in_unit_interval_property():
    grid = ["", "a", "ab", "abc", "kitten", "sitting"]
    for a in grid:
        for b in grid:
            v = levenshtein_similarity(a, b)
            assert 0.0 <= v <= 1.0


def test_similarity_monotonic_in_distance():
    # More edits -> lower or equal similarity.
    assert levenshtein_similarity("kitten", "kitten") > levenshtein_similarity("kitten", "sitting")


# --- FuzzyMatch -----------------------------------------------------------

def test_fuzzy_match_none_indices_normalized_to_empty():
    m = FuzzyMatch(text="x", score=0.5, matched_indices=None)
    assert m.matched_indices == []


def test_fuzzy_match_default_indices_empty():
    m = FuzzyMatch(text="x", score=0.5)
    assert m.matched_indices == []


# --- FuzzySearcher.search guard path --------------------------------------

def test_search_empty_query_returns_empty():
    assert FuzzySearcher().search("", ["a", "b"]) == []


def test_search_empty_texts_returns_empty():
    assert FuzzySearcher().search("a", []) == []


def test_search_whitespace_only_query_returns_empty():
    # A whitespace query is not empty, but matches nothing at min_score 0.4.
    assert FuzzySearcher().search("   ", ["kitten"]) == []


def test_search_whitespace_only_text_not_matched():
    assert FuzzySearcher().search("kitten", ["   "]) == []


# --- FuzzySearcher.search scoring -----------------------------------------

def test_search_exact_match_scores_one():
    res = FuzzySearcher().search("kitten", ["kitten", "sitting"])
    assert res[0].text == "kitten"
    assert res[0].score == 1.0


def test_search_substring_scores_point_nine():
    res = FuzzySearcher().search("cat", ["category", "dog"])
    assert [m.text for m in res] == ["category"]
    assert res[0].score == 0.9


def test_search_results_sorted_descending_by_score():
    res = FuzzySearcher().search("kitten", ["sitting", "kitten", "kit"])
    scores = [m.score for m in res]
    assert scores == sorted(scores, reverse=True)


def test_search_min_score_boundary_is_inclusive():
    # score == min_score must be included (>= comparison).
    res = FuzzySearcher(min_score=0.9).search("cat", ["category"])
    assert len(res) == 1
    assert res[0].score == 0.9


def test_search_min_score_above_one_returns_empty():
    assert FuzzySearcher(min_score=2.0).search("kitten", ["kitten"]) == []


def test_search_min_score_negative_matches_all():
    res = FuzzySearcher(min_score=-1).search("kitten", ["kitten"])
    assert len(res) == 1


def test_search_unicode_query_and_text():
    res = FuzzySearcher().search("привет", ["привет мир", "hello"])
    assert [m.text for m in res] == ["привет мир"]


def test_search_duplicate_texts_both_returned():
    # search() does not dedup the input list; both occurrences surface.
    res = FuzzySearcher().search("cat", ["cat", "cat"])
    assert [m.text for m in res] == ["cat", "cat"]


def test_search_is_idempotent():
    s = FuzzySearcher()
    r1 = s.search("kitten", ["kitten", "sitting"])
    r2 = s.search("kitten", ["kitten", "sitting"])
    assert r1 == r2


# --- FuzzySearcher.search_in_dict -----------------------------------------

def test_search_in_dict_empty_dict_returns_empty():
    assert FuzzySearcher().search_in_dict("cat", {}) == []


def test_search_in_dict_empty_query_returns_empty():
    assert FuzzySearcher().search_in_dict("", {"a": "b"}) == []


def test_search_in_dict_matches_keys_and_values():
    res = FuzzySearcher().search_in_dict("cat", {"category": "x", "dog": "y"})
    assert [m.text for m in res] == ["category"]


def test_search_in_dict_dedups_key_equal_to_value():
    # A key equal to a value is scored exactly once.
    res = FuzzySearcher().search_in_dict("cat", {"cat": "cat"})
    assert [m.text for m in res] == ["cat"]


# --- matched_indices ------------------------------------------------------

def test_search_exact_match_indices_cover_whole_text():
    m = FuzzySearcher().search("kitten", ["kitten"])[0]
    assert m.matched_indices == [0, 1, 2, 3, 4, 5]


def test_search_substring_indices_are_contiguous_prefix():
    m = FuzzySearcher().search("cat", ["category"])[0]
    assert m.matched_indices == [0, 1, 2]


def test_search_query_longer_than_text_uses_best_window():
    # Query longer than text: the whole short text is the matching region.
    m = FuzzySearcher().search("kitten", ["kit"])[0]
    assert m.matched_indices == [0, 1, 2]


# --- highlight / highlight_html -------------------------------------------

def test_highlight_empty_indices_returns_text_unchanged():
    assert FuzzySearcher().highlight("abc", []) == "abc"


def test_highlight_wraps_matched_chars_with_ansi():
    out = FuzzySearcher().highlight("abc", [0, 2])
    assert out == "\033[1ma\033[0mb\033[1mc\033[0m"


def test_highlight_html_empty_indices_returns_text_unchanged():
    assert FuzzySearcher().highlight_html("abc", []) == "abc"


def test_highlight_html_wraps_matched_chars_with_mark():
    assert FuzzySearcher().highlight_html("abc", [0]) == "<mark>a</mark>bc"


def test_highlight_html_has_no_ansi_escapes():
    out = FuzzySearcher().highlight_html("abc", [0, 1, 2])
    assert "\033" not in out
    assert out.count("<mark>") == 3


# --- search_with_highlight ------------------------------------------------

def test_search_with_highlight_plain_round_trip():
    res = FuzzySearcher().search_with_highlight("cat", ["category"])
    assert len(res) == 1
    match, highlighted = res[0]
    assert match.text == "category"
    assert "\033[1m" in highlighted
    # Every matched char is wrapped; the rest is plain.
    assert highlighted.count("\033[1m") == len(match.matched_indices)


def test_search_with_highlight_html_round_trip():
    res = FuzzySearcher().search_with_highlight("cat", ["category"], html=True)
    match, highlighted = res[0]
    assert "<mark>" in highlighted
    assert highlighted.count("<mark>") == len(match.matched_indices)


def test_search_with_highlight_empty_query_returns_empty():
    assert FuzzySearcher().search_with_highlight("", ["category"]) == []


# --- end-to-end CLI -------------------------------------------------------

def test_end_to_end_cli_init_and_search_empty_index(tmp_path):
    """End-to-end: init a data dir and run search through the installed CLI."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["search", "python", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    assert "No indexed content found" in r.output
