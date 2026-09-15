"""ARCH-70 VERIFY (VALIDATOR, cycle 224).

Pinning + adversarial tests for the ``get_items_by_tag`` non-list ``tags``
guard (Option 1: a non-list ``tags`` value is *ignored*, matching
``get_tag_counts``).

The contract under test (tickets/ARCH-70.md, docs/content-analytics.md
Contract Holes #1):

    get_items_by_tag(tag) must AGREE with get_tag_counts() on how they treat
    a non-list ``tags`` value. Before the fix, ``get_items_by_tag`` did
    ``tag in (item.get("tags") or [])`` with no isinstance guard, so a string
    ``tags`` value substring-matched (``"a" in "abc"`` -> True) while
    ``get_tag_counts`` ignored it. The two methods gave contradictory answers
    for the same item.

Option 1 (chosen by the implementer, PR #1423 @ c74fbcc) guards the body with
``isinstance(item.get("tags"), list)`` so a missing key, ``None``, and any
non-list value all yield no match - identical to ``get_tag_counts``.

These tests exercise the REAL ``get_items_by_tag`` entry point and assert the
non-list handling against the returned list (not the docstring wording), plus
the agreement property between the two methods, guard inputs, idempotence,
ordering, and one end-to-end CLI run.
"""

import subprocess
import sys

import pytest

from personal_index.content_analytics import ContentAnalytics


def make():
    return ContentAnalytics()


# ── AC 1/2/3: the divergence pin (string tags ignored, methods agree) ────


class TestStringTagsDivergencePin:
    def test_get_items_by_tag_string_tags_ignored(self):
        """AC 1: a string ``tags`` value is ignored (no substring match)."""
        a = make()
        a.add_items([{"id": 1, "tags": "abc"}])
        # Before the fix this returned [{"id": 1, "tags": "abc"}] for "a",
        # "b", "c" (substring match). Option 1: no match for any substring.
        assert a.get_items_by_tag("a") == []
        assert a.get_items_by_tag("b") == []
        assert a.get_items_by_tag("c") == []
        # Even the exact full string is not a list membership match.
        assert a.get_items_by_tag("abc") == []

    def test_get_tag_counts_string_tags_ignored_unchanged(self):
        """AC 2: get_tag_counts still ignores a string ``tags`` value."""
        a = make()
        a.add_items([{"id": 1, "tags": "abc"}])
        assert a.get_tag_counts() == {}

    def test_get_items_by_tag_and_tag_counts_agree_on_string_tags(self):
        """AC 3: the two methods AGREE on the same string-``tags`` item.

        The item is neither counted nor matched - the core of the hole.
        """
        a = make()
        a.add_items([{"id": 1, "tags": "abc"}])
        assert a.get_items_by_tag("a") == []
        assert a.get_tag_counts() == {}
        # And for every substring of the string value, agreement holds.
        for sub in ("a", "b", "c", "ab", "bc", "abc"):
            assert a.get_items_by_tag(sub) == []
        assert a.get_tag_counts() == {}


# ── AC 4: list membership unchanged ──────────────────────────────────────


class TestListMembershipUnchanged:
    def test_get_items_by_tag_list_membership_unchanged(self):
        """AC 4: a list ``tags`` value is matched by exact membership."""
        a = make()
        a.add_items([{"id": 1, "tags": ["a"]}])
        got = a.get_items_by_tag("a")
        assert [i["id"] for i in got] == [1]
        assert got[0]["tags"] == ["a"]
        # Non-member tag still yields no match.
        assert a.get_items_by_tag("b") == []

    def test_list_membership_preserves_insertion_order(self):
        """Property: matching items are returned in insertion order."""
        a = make()
        a.add_items([
            {"id": 1, "tags": ["b"]},
            {"id": 2, "tags": ["a"]},
            {"id": 3, "tags": ["a", "c"]},
            {"id": 4, "tags": ["a"]},
        ])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2, 3, 4]

    def test_list_membership_and_tag_counts_agree(self):
        """Symmetry: for a list ``tags`` value the item IS counted AND matched.

        The agreement property holds in BOTH directions - the methods only
        diverged on non-list values.
        """
        a = make()
        a.add_items([{"id": 1, "tags": ["a", "b"]}])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [1]
        assert [i["id"] for i in a.get_items_by_tag("b")] == [1]
        assert a.get_tag_counts() == {"a": 1, "b": 1}


# ── AC 5: missing / None unchanged ───────────────────────────────────────


class TestMissingAndNoneUnchanged:
    def test_missing_tags_key_no_match(self):
        """AC 5a: a missing ``tags`` key yields no match."""
        a = make()
        a.add_items([{"id": 1}, {"id": 2, "tags": ["a"]}])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2]

    def test_none_tags_key_no_match(self):
        """AC 5b: a ``None`` ``tags`` value yields no match."""
        a = make()
        a.add_items([{"id": 1, "tags": None}, {"id": 2, "tags": ["a"]}])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2]

    def test_missing_and_none_agree_with_tag_counts(self):
        """Missing / None are neither counted nor matched (agreement)."""
        a = make()
        a.add_items([{"id": 1}, {"id": 2, "tags": None}])
        assert a.get_items_by_tag("a") == []
        assert a.get_tag_counts() == {}


# ── guard inputs: empty store + non-list non-string values ───────────────


class TestGuardInputs:
    def test_empty_store_returns_empty_list(self):
        """Guard path: an empty store returns [] for any tag."""
        assert make().get_items_by_tag("a") == []

    @pytest.mark.parametrize("non_list_value", [
        "",            # empty string
        "   ",         # whitespace string
        "源",          # unicode string
        "a b",         # string with a space
        123,           # int
        1.5,           # float
        True,          # bool
        ("a",),        # tuple (NOT a list)
        {"a": 1},      # dict
        b"abc",        # bytes
    ])
    def test_non_list_non_string_values_ignored(self, non_list_value):
        """Any non-list ``tags`` value is ignored (no substring match).

        This is the adversarial sweep of the guard: the isinstance(list)
        check must reject every non-list type, not just strings.
        """
        a = make()
        a.add_items([{"id": 1, "tags": non_list_value}])
        # No match for any probe tag.
        assert a.get_items_by_tag("a") == []
        assert a.get_items_by_tag("b") == []
        # And get_tag_counts agrees: nothing counted.
        assert a.get_tag_counts() == {}

    def test_mixed_string_and_list_only_list_matches(self):
        """A string-``tags`` item and a list-``tags`` item: only the list
        item matches, and the string item is not counted."""
        a = make()
        a.add_items([
            {"id": 1, "tags": "abc"},       # string: ignored
            {"id": 2, "tags": ["a"]},       # list: matches "a"
            {"id": 3, "tags": "a"},         # string: ignored (even exact)
        ])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2]
        assert a.get_tag_counts() == {"a": 1}


# ── idempotence / property checks ────────────────────────────────────────


class TestIdempotenceAndProperties:
    def test_get_items_by_tag_is_idempotent(self):
        """Repeated calls return the same result (no mutation)."""
        a = make()
        a.add_items([
            {"id": 1, "tags": "abc"},
            {"id": 2, "tags": ["a"]},
        ])
        first = a.get_items_by_tag("a")
        second = a.get_items_by_tag("a")
        assert [i["id"] for i in first] == [i["id"] for i in second] == [2]
        # The store is unchanged by the query.
        assert a.total_items == 2
        assert a.get_tag_counts() == {"a": 1}

    def test_agreement_property_across_non_list_values(self):
        """Property: for EVERY non-list ``tags`` value, the item is neither
        counted nor matched - the two methods agree on all of them."""
        non_list_values = [
            "abc", "a", "", "   ", "源", 123, 1.5, True, ("a",), {"a": 1},
            None,
        ]
        for value in non_list_values:
            a = make()
            a.add_items([{"id": 1, "tags": value}])
            matched = a.get_items_by_tag("a")
            counted = a.get_tag_counts()
            # Agreement: if matched is empty, counted must be empty too, and
            # vice versa. For non-list values both must be empty.
            assert matched == [], f"matched non-empty for tags={value!r}"
            assert counted == {}, f"counted non-empty for tags={value!r}"

    def test_agreement_property_across_list_values(self):
        """Property: for a list ``tags`` value, the item is both counted and
        matched for each member tag (agreement in the positive direction)."""
        a = make()
        a.add_items([{"id": 1, "tags": ["x", "y", "z"]}])
        for tag in ("x", "y", "z"):
            assert [i["id"] for i in a.get_items_by_tag(tag)] == [1]
        assert a.get_tag_counts() == {"x": 1, "y": 1, "z": 1}
        # A non-member tag: not matched, not counted.
        assert a.get_items_by_tag("w") == []
        assert "w" not in a.get_tag_counts()


# ── end-to-end through the installed CLI (module entry point) ────────────


class TestCliEndToEnd:
    def test_cli_version_runs(self):
        run = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True, text=True,
        )
        assert run.returncode == 0, run.stderr
        assert run.stdout.strip() != ""
