"""Cycle 215 — negative-slice "top N" class sweep, pass 4 (QA-35).

ARCH-17 (issue #1049) is the class home: any public function that truncates a
list with ``list[:N]`` on a caller-supplied count MUST guard ``N <= 0 -> []``.
Passes 1-3 (QA-4/5/27/28) swept the whole codebase and traced every hit to its
public entry point. This pass re-runs the whole-codebase sweep
(``grep -rnE '\\[:[a-z_]+\\]' personal_index/``) and re-evaluates each
candidate with a NEGATIVE N, confirming BOTH clamps (top and bottom) before
marking it guarded.

ONE NEW unguarded public site was found that is NOT in any prior QA ticket:

``personal_index/search_suggestions.py`` — ``SearchSuggestions.suggest(prefix,
fuzzy=True)`` caps the result with ``sorted_suggestions[: self.max_suggestions]``
(line 206) with NO ``max_suggestions <= 0`` guard. When ``max_suggestions`` is
negative, the slice is ``[:-1]`` (all-but-last) instead of ``[]``.

The leak is only reachable through the FUZZY path: the exact-match path
(``_suggest_from_history`` / ``_suggest_from_tags`` / ``_suggest_from_keywords``)
gathers candidates via ``Counter.most_common(self.max_suggestions)``, and
``Counter.most_common(-1)`` returns ``[]`` — so the exact-match path is
ACCIDENTALLY masked (it returns ``[]`` for a negative bound, but for the wrong
reason). The fuzzy path adds candidates directly to the ``candidates`` dict
(not via ``most_common``), so the final ``[: self.max_suggestions]`` slice is
the only cap and it leaks.

This is inconsistent with the sibling methods in the SAME class, which DO
guard: ``get_trending(n)`` and ``get_related_queries(query, n)`` both have an
explicit ``if n <= 0: return []`` before their ``[:n]`` slice. The ``suggest``
method's docstring says it "Returns the top ``max_suggestions`` by score
descending" — a negative ``max_suggestions`` is out-of-range and must yield an
empty result, consistent with the ``0`` guard and the sibling methods.

Repro (fuzzy path leaks 4 of 5 candidates instead of 0):
    from personal_index.search_suggestions import SearchSuggestions
    s = SearchSuggestions(max_suggestions=-1, fuzzy_threshold=0.0)
    s.add_search_history(['python','pytorch','pandas','pypi','pyramid'])
    s.suggest('py', fuzzy=True)   # -> 4 suggestions (all-but-last), expect []

The defect pin below is xfail-strict so the suite stays green while the leak
exists. When the implementer adds the ``if self.max_suggestions <= 0: return []``
guard (or clamps the slice), the pin XPASSes and xfail-strict turns it red —
the signal to re-verify and close QA-35.
"""

from __future__ import annotations

import pytest

from personal_index.search_suggestions import SearchSuggestions


def _fuzzy_suggestions(max_suggestions: int) -> list[str]:
    """Build a SearchSuggestions with 5 history entries sharing the 'py' prefix
    and return the texts of ``suggest('py', fuzzy=True)`` for the given
    ``max_suggestions``. ``fuzzy_threshold=0.0`` admits every candidate so the
    fuzzy path is exercised (the path that leaks)."""
    s = SearchSuggestions(max_suggestions=max_suggestions, fuzzy_threshold=0.0)
    s.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
    return [x.text for x in s.suggest("py", fuzzy=True)]


# ---------------------------------------------------------------------------
# QA-35 defect pins (xfail-strict) — suggest(fuzzy=True) with negative
# max_suggestions leaks all-but-last instead of []
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="QA-35: suggest(fuzzy=True) with max_suggestions=-1 leaks "
    "all-but-last ([:-1]) instead of []; the fuzzy path adds candidates "
    "directly so the [:max_suggestions] slice is the only cap and it has no "
    "N<=0 guard. Inconsistent with sibling get_trending/get_related_queries "
    "which guard n<=0 -> [].",
)
class TestSuggestFuzzyNegativeMaxSuggestions:
    def test_fuzzy_negative_max_suggestions_returns_empty(self):
        # max_suggestions=-1 is out-of-range; contract says return [] (== 0)
        assert _fuzzy_suggestions(-1) == []

    def test_fuzzy_negative_max_suggestions_returns_nothing(self):
        # all-but-last is the leak: 4 of 5 candidates must NOT be returned
        assert len(_fuzzy_suggestions(-1)) == 0

    def test_fuzzy_negative_max_suggestions_matches_zero_guard(self):
        # a negative bound must behave identically to the 0 guard
        assert _fuzzy_suggestions(-1) == _fuzzy_suggestions(0)


# ---------------------------------------------------------------------------
# clean armor — the 0 guard and positive bounds already work (not xfail)
# ---------------------------------------------------------------------------


class TestSuggestFuzzyArmor:
    def test_fuzzy_zero_max_suggestions_returns_empty(self):
        # the 0 guard already works - clean armor
        assert _fuzzy_suggestions(0) == []

    def test_fuzzy_positive_max_suggestions_caps(self):
        # valid bound returns exactly that many - clean armor
        assert len(_fuzzy_suggestions(2)) == 2

    def test_fuzzy_positive_max_suggestions_all_when_small(self):
        # bound larger than the candidate count returns all 5 - clean armor
        assert len(_fuzzy_suggestions(10)) == 5

    def test_exact_match_negative_max_suggestions_returns_empty(self):
        # the exact-match path is accidentally masked by
        # Counter.most_common(-1) -> [] (returns [] for the wrong reason);
        # pin it so a refactor that removes the most_common cap does not
        # silently turn the exact-match path into a leak too.
        s = SearchSuggestions(max_suggestions=-1)
        s.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
        assert [x.text for x in s.suggest("py")] == []

    def test_sibling_get_trending_negative_guarded(self):
        # sibling method in the same class already guards n<=0 -> []
        s = SearchSuggestions()
        for q in ["a", "b", "c"]:
            s.record_search(q)
        assert s.get_trending(-1) == []

    def test_sibling_get_related_queries_negative_guarded(self):
        # sibling method in the same class already guards n<=0 -> []
        s = SearchSuggestions()
        s.add_search_history(["foo bar", "foo baz", "foo qux"])
        assert [x.text for x in s.get_related_queries("foo", -1)] == []
