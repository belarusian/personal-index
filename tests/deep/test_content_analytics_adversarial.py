"""Adversarial deep tests for personal_index.content_analytics.ContentAnalytics.

Cycle 188 (VALIDATOR). ContentAnalytics is a self-contained library module
(not wired into the CLI). These tests attack the documented contracts with
guard inputs (None/empty/whitespace/unicode/duplicate/out-of-range),
round-trips, idempotence, ordering/stability, boundary lengths, and a
defensive-load pass, plus one end-to-end CLI run.

DEFECT QA-22 (xfail-strict pins, do NOT fix here):
    get_title_lengths / get_description_lengths compute
    ``len(str(item.get("title", "")))``. A *present* ``None`` value is
    coerced by ``str()`` to the 4-character string ``"None"``, so a None
    title/description reports length 4 instead of 0. A *missing* key
    correctly reports 0 (the default ``""`` is used). The two cases that
    both mean "no text" disagree, corrupting get_avg_title_length /
    get_avg_description_length.
"""

import subprocess
import sys

import pytest

from personal_index.content_analytics import ContentAnalytics


def make():
    return ContentAnalytics()


# ── init / empty-state guards ────────────────────────────────────────────


class TestEmptyState:
    def test_init_zero_items(self):
        a = make()
        assert a.total_items == 0

    def test_empty_tag_counts(self):
        assert make().get_tag_counts() == {}

    def test_empty_title_lengths(self):
        assert make().get_title_lengths() == []

    def test_empty_avg_title_length_is_zero(self):
        assert make().get_avg_title_length() == 0.0

    def test_empty_description_lengths(self):
        assert make().get_description_lengths() == []

    def test_empty_avg_description_length_is_zero(self):
        assert make().get_avg_description_length() == 0.0

    def test_empty_items_with_links(self):
        assert make().get_items_with_links() == []

    def test_empty_link_ratio_is_zero(self):
        assert make().get_link_ratio() == 0.0

    def test_empty_tag_distribution(self):
        assert make().get_tag_distribution() == {}

    def test_empty_unique_tags_count(self):
        assert make().get_unique_tags_count() == 0

    def test_empty_get_items_by_tag(self):
        assert make().get_items_by_tag("anything") == []


# ── add_items guards ─────────────────────────────────────────────────────


class TestAddItems:
    def test_add_empty_list(self):
        a = make()
        a.add_items([])
        assert a.total_items == 0

    def test_add_multiple_batches_accumulate(self):
        a = make()
        a.add_items([{"title": "a"}])
        a.add_items([{"title": "b"}, {"title": "c"}])
        assert a.total_items == 3

    def test_add_none_items_raises(self):
        a = make()
        with pytest.raises(TypeError):
            a.add_items(None)

    def test_add_items_does_not_mutate_input_order(self):
        a = make()
        items = [{"title": "x"}, {"title": "y"}]
        a.add_items(items)
        assert items == [{"title": "x"}, {"title": "y"}]


# ── title / description length contracts ─────────────────────────────────


class TestTitleLengths:
    def test_missing_title_is_zero(self):
        a = make()
        a.add_items([{}])
        assert a.get_title_lengths() == [0]

    def test_empty_title_is_zero(self):
        a = make()
        a.add_items([{"title": ""}])
        assert a.get_title_lengths() == [0]

    def test_whitespace_title_counts_chars(self):
        a = make()
        a.add_items([{"title": "   " }])
        assert a.get_title_lengths() == [3]

    def test_unicode_title_counts_code_points(self):
        a = make()
        a.add_items([{"title": "源🔥"}])
        # len() counts code points: 源(1) + 🔥(1) == 2
        assert a.get_title_lengths() == [2]

    def test_non_string_title_is_stringified(self):
        a = make()
        a.add_items([{"title": 123}])
        assert a.get_title_lengths() == [3]

    def test_avg_title_length_basic(self):
        a = make()
        a.add_items([{"title": "ab"}, {"title": "abcd"}])
        assert a.get_avg_title_length() == 3.0

    def test_avg_title_length_round_trip(self):
        a = make()
        a.add_items([{"title": "abc"}, {"title": "a"}])
        assert a.get_avg_title_length() == 2.0


class TestDescriptionLengths:
    def test_missing_description_is_zero(self):
        a = make()
        a.add_items([{}])
        assert a.get_description_lengths() == [0]

    def test_empty_description_is_zero(self):
        a = make()
        a.add_items([{"description": ""}])
        assert a.get_description_lengths() == [0]

    def test_avg_description_length_basic(self):
        a = make()
        a.add_items([{"description": "ab"}, {"description": "abcd"}])
        assert a.get_avg_description_length() == 3.0


# ── DEFECT QA-22: None title/description coerced to "None" (length 4) ────


class TestNoneTitleCoercion:
    """QA-22: a present None title/description must behave like a missing
    one (length 0), not be stringified to the 4-char literal "None"."""

    def test_none_title_is_zero_length(self):
        a = make()
        a.add_items([{"title": None}])
        assert a.get_title_lengths() == [0]

    def test_none_title_does_not_inflate_average(self):
        a = make()
        a.add_items([{"title": None}, {"title": "ab"}])
        # None -> 0, "ab" -> 2 => avg 1.0. The bug yields (4 + 2) / 2 == 3.0.
        assert a.get_avg_title_length() == 1.0

    def test_none_description_is_zero_length(self):
        a = make()
        a.add_items([{"description": None}])
        assert a.get_description_lengths() == [0]

    def test_none_description_does_not_inflate_average(self):
        a = make()
        a.add_items([{"description": None}, {"description": "ab"}])
        assert a.get_avg_description_length() == 1.0


# ── tag contracts ────────────────────────────────────────────────────────


class TestTags:
    def test_tag_counts_basic(self):
        a = make()
        a.add_items([
            {"tags": ["a", "b"]},
            {"tags": ["a"]},
        ])
        assert a.get_tag_counts() == {"a": 2, "b": 1}

    def test_missing_tags_ignored(self):
        a = make()
        a.add_items([{}, {"tags": ["a"]}])
        assert a.get_tag_counts() == {"a": 1}

    def test_non_list_tags_ignored(self):
        a = make()
        a.add_items([{"tags": "not-a-list"}, {"tags": ["a"]}])
        assert a.get_tag_counts() == {"a": 1}

    def test_none_tags_ignored(self):
        a = make()
        a.add_items([{"tags": None}, {"tags": ["a"]}])
        assert a.get_tag_counts() == {"a": 1}

    def test_duplicate_tags_counted(self):
        a = make()
        a.add_items([{"tags": ["a", "a", "a"]}])
        assert a.get_tag_counts() == {"a": 3}

    def test_unicode_tags(self):
        a = make()
        a.add_items([{"tags": ["源", "源"]}])
        assert a.get_tag_counts() == {"源": 2}

    def test_unique_tags_count(self):
        a = make()
        a.add_items([
            {"tags": ["a", "b"]},
            {"tags": ["b", "c"]},
        ])
        assert a.get_unique_tags_count() == 3

    def test_tag_distribution_percentages_sum_to_100(self):
        a = make()
        a.add_items([
            {"tags": ["a", "a"]},
            {"tags": ["b"]},
        ])
        dist = a.get_tag_distribution()
        assert dist["a"] == pytest.approx(200.0 / 3)
        assert dist["b"] == pytest.approx(100.0 / 3)
        assert sum(dist.values()) == pytest.approx(100.0)

    def test_tag_distribution_empty_when_no_tags(self):
        a = make()
        a.add_items([{}, {"tags": []}])
        assert a.get_tag_distribution() == {}

    def test_get_items_by_tag_returns_matching(self):
        a = make()
        a.add_items([
            {"id": 1, "tags": ["a"]},
            {"id": 2, "tags": ["b"]},
            {"id": 3, "tags": ["a", "c"]},
        ])
        got = a.get_items_by_tag("a")
        assert [i["id"] for i in got] == [1, 3]

    def test_get_items_by_tag_missing_tags_key(self):
        a = make()
        a.add_items([{"id": 1}, {"id": 2, "tags": ["a"]}])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2]

    def test_get_items_by_tag_none_tags_key(self):
        a = make()
        a.add_items([{"id": 1, "tags": None}, {"id": 2, "tags": ["a"]}])
        assert [i["id"] for i in a.get_items_by_tag("a")] == [2]

    def test_get_items_by_tag_no_match(self):
        a = make()
        a.add_items([{"tags": ["a"]}])
        assert a.get_items_by_tag("zzz") == []


# ── link contracts ───────────────────────────────────────────────────────


class TestLinks:
    def test_items_with_links_filters_falsy(self):
        a = make()
        a.add_items([
            {"id": 1, "link": "http://x"},
            {"id": 2},
            {"id": 3, "link": ""},
            {"id": 4, "link": None},
        ])
        assert [i["id"] for i in a.get_items_with_links()] == [1]

    def test_link_ratio_all_linked(self):
        a = make()
        a.add_items([{"link": "a"}, {"link": "b"}])
        assert a.get_link_ratio() == 1.0

    def test_link_ratio_none_linked(self):
        a = make()
        a.add_items([{}, {}])
        assert a.get_link_ratio() == 0.0

    def test_link_ratio_half(self):
        a = make()
        a.add_items([{"link": "a"}, {}])
        assert a.get_link_ratio() == 0.5


# ── idempotence / round-trip / ordering ──────────────────────────────────


class TestIdempotenceAndOrdering:
    def test_getters_are_idempotent(self):
        a = make()
        a.add_items([{"title": "abc", "tags": ["x"], "link": "l"}])
        first = a.get_title_lengths()
        second = a.get_title_lengths()
        assert first == second
        assert a.get_tag_counts() == a.get_tag_counts()
        assert a.total_items == a.total_items

    def test_add_then_clear_round_trip(self):
        a = make()
        a.add_items([{"title": "abc"}])
        assert a.total_items == 1
        a.clear()
        assert a.total_items == 0
        assert a.get_title_lengths() == []
        assert a.get_tag_counts() == {}

    def test_clear_is_idempotent(self):
        a = make()
        a.clear()
        a.clear()
        assert a.total_items == 0

    def test_title_lengths_preserve_insertion_order(self):
        a = make()
        a.add_items([{"title": "a"}, {"title": "bb"}, {"title": "ccc"}])
        assert a.get_title_lengths() == [1, 2, 3]

    def test_items_with_links_preserve_insertion_order(self):
        a = make()
        a.add_items([
            {"id": 1, "link": "a"},
            {"id": 2},
            {"id": 3, "link": "c"},
        ])
        assert [i["id"] for i in a.get_items_with_links()] == [1, 3]


# ── boundary / out-of-range lengths ──────────────────────────────────────


class TestBoundaryLengths:
    def test_single_char_title(self):
        a = make()
        a.add_items([{"title": "a"}])
        assert a.get_title_lengths() == [1]

    def test_long_title(self):
        a = make()
        a.add_items([{"title": "x" * 10000}])
        assert a.get_title_lengths() == [10000]

    def test_avg_with_many_items(self):
        a = make()
        a.add_items([{"title": "a" * i} for i in range(1, 101)])
        # sum(1..100) / 100 == 5050 / 100 == 50.5
        assert a.get_avg_title_length() == pytest.approx(50.5)


# ── defensive load: mixed / malformed items do not crash ─────────────────


class TestDefensiveLoad:
    def test_mixed_malformed_items_do_not_crash(self):
        a = make()
        a.add_items([
            {"title": "ok", "tags": ["a"], "link": "l", "description": "d"},
            {},
            {"title": None, "tags": None, "link": None, "description": None},
            {"title": 42, "tags": "bad", "link": 0, "description": 7},
        ])
        # Should not raise; total reflects all four items.
        assert a.total_items == 4
        assert isinstance(a.get_title_lengths(), list)
        assert isinstance(a.get_tag_counts(), dict)
        assert isinstance(a.get_link_ratio(), float)

    def test_empty_string_everywhere(self):
        a = make()
        a.add_items([{"title": "", "tags": [], "link": "", "description": ""}])
        assert a.get_title_lengths() == [0]
        assert a.get_description_lengths() == [0]
        assert a.get_tag_counts() == {}
        assert a.get_link_ratio() == 0.0


# ── end-to-end through the installed CLI (module entry point) ────────────


class TestCliEndToEnd:
    def test_cli_version_runs(self):
        run = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True, text=True,
        )
        assert run.returncode == 0, run.stderr
        assert run.stdout.strip() != ""
