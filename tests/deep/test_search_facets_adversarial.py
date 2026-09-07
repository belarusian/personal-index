"""Cycle 133 VALIDATOR probe: adversarial tests for personal_index.search_facets.

Attacks the exact-contract docstrings merged for FacetBuilder.build /
FacetBuilder.aggregate / Facet.add_value / Facet.sort_values (PRs #981/#973
era, TICKET-550/547) with guard inputs (None/empty/unicode/duplicate/
out-of-range), round-trips, idempotence, and one end-to-end CLI run.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.search_facets.facet import Facet, FacetType, FacetValue
from personal_index.search_facets.facet_builder import FacetBuilder


class TestBuildGuardPaths:
    def setup_method(self):
        self.b = FacetBuilder()

    def test_empty_items_returns_empty_dict(self):
        assert self.b.build([], ["tags"]) == {}

    def test_empty_facet_fields_returns_empty_dict(self):
        assert self.b.build([{"tags": ["a"]}], []) == {}

    def test_field_missing_everywhere_is_skipped(self):
        # Contract: "A field whose facet ends up with no values is skipped."
        out = self.b.build([{"tags": ["a"]}, {"tags": ["b"]}], ["nonexistent"])
        assert out == {}

    def test_none_values_are_skipped_not_stringified(self):
        # _extract_values returns [] for None -> facet has no values -> skipped.
        out = self.b.build([{"x": None}], ["x"])
        assert out == {}

    def test_non_dict_intermediate_path_yields_empty(self):
        out = self.b.build([{"meta": "string-not-dict"}], ["meta.key"])
        assert out == {}

    def test_missing_intermediate_key_yields_empty(self):
        out = self.b.build([{"meta": {}}], ["meta.key"])
        assert out == {}


class TestBuildContract:
    def setup_method(self):
        self.b = FacetBuilder()

    def test_values_stringified(self):
        # Contract: "each value is stringified (str(value))".
        out = self.b.build([{"score": 1}, {"score": 2.5}, {"score": True}], ["score"])
        names = {v.name for v in out["score"].values}
        assert names == {"1", "2.5", "True"}

    def test_duplicates_aggregate_into_one_value(self):
        out = self.b.build([{"tags": "a"}, {"tags": "a"}, {"tags": "b"}], ["tags"])
        counts = {v.name: v.count for v in out["tags"].values}
        assert counts == {"a": 2, "b": 1}

    def test_sort_then_truncate_keeps_highest_counts(self):
        # Contract: "sorted by count descending and then truncated to the top
        # max_values (the highest-count values are kept)".
        items = [{"t": "hi"}] * 5 + [{"t": "mid"}] * 3 + [{"t": "lo"}]
        out = self.b.build(items, ["t"], max_values=2)
        names = [v.name for v in out["t"].values]
        assert names == ["hi", "mid"]

    def test_max_values_zero_yields_empty_values_facet(self):
        # Adversarial out-of-range: docstring says truncate to top max_values;
        # 0 must yield an empty values list (facet itself still present since
        # it had values before truncation).
        out = self.b.build([{"t": "a"}], ["t"], max_values=0)
        assert "t" in out
        assert out["t"].values == []

    def test_unicode_values_roundtrip(self):
        items = [{"t": "日本語"}, {"t": "é"}, {"t": "日本"}]
        out = self.b.build(items, ["t"])
        names = {v.name for v in out["t"].values}
        assert names == {"日本語", "é", "日本"}

    def test_type_resolution_full_name_beats_base_name(self):
        out = self.b.build(
            [{"meta": {"tags": "x"}}], ["meta.tags"],
            facet_types={"meta.tags": "number", "tags": "category"},
        )
        assert out["meta.tags"].facet_type is FacetType.NUMBER

    def test_type_resolution_base_name_fallback(self):
        out = self.b.build(
            [{"meta": {"tags": "x"}}], ["meta.tags"],
            facet_types={"tags": "category"},
        )
        assert out["meta.tags"].facet_type is FacetType.CATEGORY

    def test_invalid_custom_type_falls_back_to_default(self):
        # "tags" default is TAG; invalid custom string must not crash.
        out = self.b.build([{"tags": "x"}], ["tags"], facet_types={"tags": "bogus"})
        assert out["tags"].facet_type is FacetType.TAG

    def test_unknown_field_defaults_to_string(self):
        out = self.b.build([{"zzz": "x"}], ["zzz"])
        assert out["zzz"].facet_type is FacetType.STRING


class TestAggregateContract:
    def setup_method(self):
        self.b = FacetBuilder()

    def test_both_empty(self):
        assert self.b.aggregate({}, {}) == {}

    def test_pass_through_by_reference(self):
        # Contract: "that facet object is passed through by reference (not copied)".
        fa = Facet(name="a", facet_type=FacetType.STRING)
        fa.add_value("x")
        out = self.b.aggregate({"a": fa}, {})
        assert out["a"] is fa

    def test_union_sum_and_resort(self):
        fa = Facet(name="t", facet_type=FacetType.CATEGORY)
        fa.add_value("x", 2)
        fa.add_value("y", 5)
        fb = Facet(name="t", facet_type=FacetType.STRING)
        fb.add_value("x", 3)
        out = self.b.aggregate({"t": fa}, {"t": fb})
        counts = {v.name: v.count for v in out["t"].values}
        assert counts == {"x": 5, "y": 5}
        assert [v.count for v in out["t"].values] == [5, 5]
        # type taken from facets_a
        assert out["t"].facet_type is FacetType.CATEGORY

    def test_aggregate_idempotent_on_disjoint_keys(self):
        fa = Facet(name="a")
        fa.add_value("x", 1)
        fb = Facet(name="b")
        fb.add_value("y", 2)
        once = self.b.aggregate({"a": fa}, {"b": fb})
        twice = self.b.aggregate(once, {})
        assert set(twice) == {"a", "b"}
        assert twice["a"].values[0].count == 1


class TestFacetUnit:
    def test_add_value_increments_not_replaces(self):
        f = Facet(name="f")
        f.add_value("x", 2)
        f.add_value("x", 3)
        assert len(f.values) == 1
        assert f.values[0].count == 5

    def test_sort_values_stable_on_ties(self):
        f = Facet(name="f")
        f.add_value("a", 1)
        f.add_value("b", 1)
        f.add_value("c", 2)
        f.sort_values()
        assert [v.name for v in f.values] == ["c", "a", "b"]

    def test_to_dict_from_dict_roundtrip(self):
        f = Facet(name="f", facet_type=FacetType.TAG)
        f.add_value("x", 2)
        f.add_value("y", 1)
        g = Facet.from_dict(f.to_dict())
        assert g.name == f.name
        assert g.facet_type is f.facet_type
        assert [(v.name, v.count) for v in g.values] == [("x", 2), ("y", 1)]

    def test_facet_value_roundtrip(self):
        v = FacetValue(name="n", count=7)
        assert FacetValue.from_dict(v.to_dict()) == v


class TestCliEndToEnd:
    def test_init_then_search_empty_index(self, tmp_path):
        # End-to-end: init a data dir, then search an empty index -> the
        # documented "No indexed content found." notice, exit code 0.
        env_dir = str(tmp_path / "dd")
        r1 = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r1.returncode == 0, r1.stderr
        r2 = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "hello",
             "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r2.returncode == 0, r2.stderr
        assert "No indexed content found" in r2.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
