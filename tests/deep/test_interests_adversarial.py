"""Adversarial deep tests for personal_index.interests (InterestStore).

Cycle 183 — VALIDATOR probe.

Covers: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, ordering/stability, boundary lengths,
defensive loads, error/rollback contracts, and one end-to-end run
through the installed CLI entry point.

Contracts under test (from docstrings):
- InterestStore(store_path=None) is in-memory only; a store_path that
  exists is loaded in __post_init__; a missing store_path is NOT an error.
- _load: corrupt JSON / non-dict JSON / non-dict value -> empty store
  (defensive, no raise).
- add: replaces an existing interest with the same name; persists.
- remove: returns True and persists on hit, False on miss (no save).
- get: returns the Interest or None.
- list_all / get_enabled: list of Interest; get_enabled filters enabled.
- toggle: flips enabled, persists, returns the Interest; None on miss.
- get_all_keywords / get_all_topics: lowercase set across interests.
- get_all_url_patterns: compiled patterns; non-str skipped; re.error
  patterns skipped (not raised).
- update_priority: clamps 1-10, persists, returns Interest; None on miss.
- matches_any: interests whose Interest.matches(text,url) is True.
- clear: empties and persists.
- total_score: sum of Interest.score(text).
- Interest.__post_init__: "Clamp priority to 1-10"; keywords passed as
  int (positional priority) -> priority=that int, keywords=[].
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from personal_index.interests import InterestStore
from personal_index.models import Interest, InterestType, MatchMode


def _mk(name: str, **kw) -> Interest:
    return Interest(name=name, **kw)


@pytest.fixture
def mem() -> InterestStore:
    """In-memory store (no persistence)."""
    return InterestStore(store_path=None)


@pytest.fixture
def file_store(tmp_path) -> InterestStore:
    """Store backed by a temp file."""
    return InterestStore(store_path=str(tmp_path / "interests.json"))


# ---------------------------------------------------------------------------
# Construction / defensive loads
# ---------------------------------------------------------------------------

class TestConstructionAndLoads:
    def test_none_path_is_in_memory(self, mem):
        assert mem.list_all() == []

    def test_missing_file_path_is_empty_not_error(self, tmp_path):
        s = InterestStore(store_path=str(tmp_path / "nope.json"))
        assert s.list_all() == []

    def test_loads_existing_file(self, tmp_path):
        p = tmp_path / "i.json"
        p.write_text(json.dumps({"a": _mk("a", keywords=["x"]).to_dict()}))
        s = InterestStore(store_path=str(p))
        assert [i.name for i in s.list_all()] == ["a"]

    def test_corrupt_json_loads_empty(self, tmp_path):
        p = tmp_path / "i.json"
        p.write_text("{not valid json")
        s = InterestStore(store_path=str(p))
        assert s.list_all() == []

    def test_non_dict_json_loads_empty(self, tmp_path):
        p = tmp_path / "i.json"
        p.write_text("[1, 2, 3]")
        s = InterestStore(store_path=str(p))
        assert s.list_all() == []

    def test_null_json_loads_empty(self, tmp_path):
        p = tmp_path / "i.json"
        p.write_text("null")
        s = InterestStore(store_path=str(p))
        assert s.list_all() == []

    def test_non_dict_value_gracefully_degrades_to_empty(self, tmp_path):
        # value is a list -> Interest.from_dict(list) -> .get raises
        # AttributeError which IS now in the except tuple -> caught.
        # QA-20: defensive-load-crash sweep broadens except tuples.
        p = tmp_path / "i.json"
        p.write_text(json.dumps({"a": ["not", "a", "dict"]}))
        s = InterestStore(store_path=str(p))
        assert s.list_all() == []


# ---------------------------------------------------------------------------
# add / remove / get
# ---------------------------------------------------------------------------

class TestAddRemoveGet:
    def test_add_then_get(self, mem):
        mem.add(_mk("a", keywords=["x"]))
        assert mem.get("a") is not None
        assert mem.get("a").keywords == ["x"]

    def test_get_missing_returns_none(self, mem):
        assert mem.get("nope") is None

    def test_add_replaces_same_name(self, mem):
        mem.add(_mk("a", keywords=["x"]))
        mem.add(_mk("a", keywords=["y"]))
        assert mem.get("a").keywords == ["y"]
        assert len(mem.list_all()) == 1

    def test_remove_hit_returns_true(self, mem):
        mem.add(_mk("a"))
        assert mem.remove("a") is True
        assert mem.get("a") is None

    def test_remove_miss_returns_false(self, mem):
        assert mem.remove("nope") is False

    def test_remove_idempotent(self, mem):
        mem.add(_mk("a"))
        assert mem.remove("a") is True
        assert mem.remove("a") is False

    def test_add_persists_to_file(self, file_store):
        file_store.add(_mk("a", keywords=["x"]))
        reloaded = InterestStore(store_path=file_store.store_path)
        assert reloaded.get("a").keywords == ["x"]

    def test_remove_persists_to_file(self, file_store):
        file_store.add(_mk("a"))
        file_store.remove("a")
        reloaded = InterestStore(store_path=file_store.store_path)
        assert reloaded.get("a") is None

    def test_unicode_name_roundtrip(self, mem):
        name = "интерес-日本語-🚀"
        mem.add(_mk(name, keywords=["ключ"]))
        assert mem.get(name).keywords == ["ключ"]

    def test_empty_name_allowed(self, mem):
        mem.add(_mk(""))
        assert mem.get("") is not None


# ---------------------------------------------------------------------------
# list_all / get_enabled / ordering
# ---------------------------------------------------------------------------

class TestListAndEnabled:
    def test_list_all_empty(self, mem):
        assert mem.list_all() == []

    def test_list_all_returns_copy(self, mem):
        mem.add(_mk("a"))
        lst = mem.list_all()
        lst.clear()
        assert len(mem.list_all()) == 1

    def test_get_enabled_filters(self, mem):
        mem.add(_mk("on", enabled=True))
        mem.add(_mk("off", enabled=False))
        assert [i.name for i in mem.get_enabled()] == ["on"]

    def test_get_enabled_empty(self, mem):
        assert mem.get_enabled() == []

    def test_ordering_stable_insertion(self, mem):
        for n in ["c", "a", "b"]:
            mem.add(_mk(n))
        assert [i.name for i in mem.list_all()] == ["c", "a", "b"]


# ---------------------------------------------------------------------------
# toggle
# ---------------------------------------------------------------------------

class TestToggle:
    def test_toggle_flips_enabled(self, mem):
        mem.add(_mk("a", enabled=True))
        r = mem.toggle("a")
        assert r is not None and r.enabled is False
        assert mem.get("a").enabled is False

    def test_toggle_idempotent_pair(self, mem):
        mem.add(_mk("a", enabled=True))
        mem.toggle("a")
        mem.toggle("a")
        assert mem.get("a").enabled is True

    def test_toggle_missing_returns_none(self, mem):
        assert mem.toggle("nope") is None

    def test_toggle_persists(self, file_store):
        file_store.add(_mk("a", enabled=True))
        file_store.toggle("a")
        reloaded = InterestStore(store_path=file_store.store_path)
        assert reloaded.get("a").enabled is False


# ---------------------------------------------------------------------------
# keyword / topic / url-pattern aggregation
# ---------------------------------------------------------------------------

class TestAggregation:
    def test_get_all_keywords_lowercased(self, mem):
        mem.add(_mk("a", keywords=["Python", "Django"]))
        assert mem.get_all_keywords() == {"python", "django"}

    def test_get_all_keywords_empty(self, mem):
        assert mem.get_all_keywords() == set()

    def test_get_all_keywords_skips_non_str(self, mem):
        mem.add(_mk("a", keywords=["ok", 42, None]))
        assert mem.get_all_keywords() == {"ok"}

    def test_get_all_topics_lowercased(self, mem):
        mem.add(_mk("a", topics=["Web", "API"]))
        assert mem.get_all_topics() == {"web", "api"}

    def test_get_all_topics_empty(self, mem):
        assert mem.get_all_topics() == set()

    def test_get_all_topics_skips_non_str(self, mem):
        mem.add(_mk("a", topics=["ok", 42, None]))
        assert mem.get_all_topics() == {"ok"}

    def test_get_all_url_patterns_compiles(self, mem):
        mem.add(_mk("a", url_patterns=["^https://", "example\\.com"]))
        pats = mem.get_all_url_patterns()
        assert len(pats) == 2
        assert pats[0].pattern == "^https://"

    def test_get_all_url_patterns_skips_non_str(self, mem):
        mem.add(_mk("a", url_patterns=[42, None, "ok"]))
        pats = mem.get_all_url_patterns()
        assert len(pats) == 1 and pats[0].pattern == "ok"

    def test_get_all_url_patterns_skips_invalid_regex(self, mem):
        # "[unclosed" is a re.error; must be skipped, not raised.
        mem.add(_mk("a", url_patterns=["[unclosed", "good"]))
        pats = mem.get_all_url_patterns()
        assert [p.pattern for p in pats] == ["good"]

    def test_get_all_url_patterns_empty(self, mem):
        assert mem.get_all_url_patterns() == []


# ---------------------------------------------------------------------------
# update_priority (clamp 1-10)
# ---------------------------------------------------------------------------

class TestUpdatePriority:
    def test_update_priority_in_range(self, mem):
        mem.add(_mk("a", priority=5))
        r = mem.update_priority("a", 7)
        assert r is not None and r.priority == 7

    def test_update_priority_clamps_high(self, mem):
        mem.add(_mk("a", priority=5))
        r = mem.update_priority("a", 99)
        assert r.priority == 10

    def test_update_priority_clamps_low(self, mem):
        mem.add(_mk("a", priority=5))
        r = mem.update_priority("a", -3)
        assert r.priority == 1

    def test_update_priority_missing_returns_none(self, mem):
        assert mem.update_priority("nope", 5) is None

    def test_update_priority_persists(self, file_store):
        file_store.add(_mk("a", priority=5))
        file_store.update_priority("a", 9)
        reloaded = InterestStore(store_path=file_store.store_path)
        assert reloaded.get("a").priority == 9


# ---------------------------------------------------------------------------
# matches_any / total_score
# ---------------------------------------------------------------------------

class TestMatchesAndScore:
    def test_matches_any_by_keyword(self, mem):
        mem.add(_mk("a", keywords=["python"]))
        mem.add(_mk("b", keywords=["ruby"]))
        got = mem.matches_any("learning python today")
        assert [i.name for i in got] == ["a"]

    def test_matches_any_none(self, mem):
        mem.add(_mk("a", keywords=["python"]))
        assert mem.matches_any("nothing here") == []

    def test_matches_any_disabled_excluded(self, mem):
        mem.add(_mk("a", keywords=["python"], enabled=False))
        assert mem.matches_any("python") == []

    def test_matches_any_by_url(self, mem):
        mem.add(_mk("a", url_patterns=["example\\.com"]))
        got = mem.matches_any("", "https://example.com/x")
        assert [i.name for i in got] == ["a"]

    def test_matches_any_empty_store(self, mem):
        assert mem.matches_any("anything") == []

    def test_total_score_sums(self, mem):
        mem.add(_mk("a", keywords=["x"], priority=2))
        mem.add(_mk("b", keywords=["x"], priority=3))
        # each counts "x" once -> 1*2 + 1*3 = 5
        assert mem.total_score("x") == 5.0

    def test_total_score_disabled_zero(self, mem):
        mem.add(_mk("a", keywords=["x"], priority=5, enabled=False))
        assert mem.total_score("x") == 0.0

    def test_total_score_empty(self, mem):
        assert mem.total_score("x") == 0.0


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_empties(self, mem):
        mem.add(_mk("a"))
        mem.add(_mk("b"))
        mem.clear()
        assert mem.list_all() == []

    def test_clear_idempotent(self, mem):
        mem.clear()
        mem.clear()
        assert mem.list_all() == []

    def test_clear_persists(self, file_store):
        file_store.add(_mk("a"))
        file_store.clear()
        reloaded = InterestStore(store_path=file_store.store_path)
        assert reloaded.list_all() == []


# ---------------------------------------------------------------------------
# Round-trip / serialization
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_full_roundtrip(self, file_store):
        i = _mk(
            "a",
            interest_type=InterestType.TOPIC,
            value="v",
            keywords=["k1", "k2"],
            url_patterns=["p1"],
            topics=["t1"],
            priority=8,
            enabled=False,
            match_mode=MatchMode.ALL,
        )
        file_store.add(i)
        reloaded = InterestStore(store_path=file_store.store_path)
        r = reloaded.get("a")
        assert r.interest_type == InterestType.TOPIC
        assert r.value == "v"
        assert r.keywords == ["k1", "k2"]
        assert r.url_patterns == ["p1"]
        assert r.topics == ["t1"]
        assert r.priority == 8
        assert r.enabled is False
        assert r.match_mode == MatchMode.ALL

    def test_to_dict_from_dict_roundtrip(self):
        i = _mk("a", keywords=["x"], priority=3)
        d = i.to_dict()
        j = Interest.from_dict(d)
        assert j.name == "a" and j.keywords == ["x"] and j.priority == 3


# ---------------------------------------------------------------------------
# Interest.__post_init__ priority clamp contract
# ---------------------------------------------------------------------------

class TestInterestPostInitClamp:
    def test_priority_clamped_high(self):
        assert _mk("a", priority=99).priority == 10

    def test_priority_clamped_low(self):
        assert _mk("a", priority=-5).priority == 1

    def test_priority_in_range_unchanged(self):
        assert _mk("a", priority=7).priority == 7

    def test_keywords_as_int_becomes_priority(self):
        # Documented: "Handle edge case where keywords is passed as int
        # (positional priority)." -> the int is consumed as priority and
        # keywords is reset to []. (The clamp contract for this path is
        # pinned separately by the xfail test below, QA-19.)
        i = Interest("a", "keyword", "v", 99)
        assert i.keywords == []

    def test_keywords_as_int_negative_keywords_reset(self):
        i = Interest("a", "keyword", "v", -5)
        assert i.keywords == []

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-19: Interest.__post_init__ docstring claims 'Clamp priority "
            "to 1-10' but the keywords-as-int path assigns the raw int "
            "without clamping (priority=99 stays 99, -5 stays -5)."
        ),
    )
    def test_keywords_as_int_priority_is_clamped(self):
        i = Interest("a", "keyword", "v", 99)
        assert i.priority == 10

    def test_keywords_non_list_coerced(self):
        i = Interest("a", "keyword", "v", "not-a-list")
        assert i.keywords == []


# ---------------------------------------------------------------------------
# End-to-end: installed CLI entry point
# ---------------------------------------------------------------------------

class TestEndToEndCLI:
    def test_cli_interests_add_list_remove(self, tmp_path):
        dd = str(tmp_path / "data")
        runner_cmd = [sys.executable, "-m", "personal_index.cli"]
        # add
        p1 = subprocess.run(
            runner_cmd + ["interests", "add", "-n", "python",
                          "-k", "python", "-k", "django",
                          "--data-dir", dd],
            capture_output=True, text=True,
        )
        assert p1.returncode == 0, p1.stderr
        assert "Added interest: python" in p1.stdout

        # list
        p2 = subprocess.run(
            runner_cmd + ["interests", "list", "--data-dir", dd],
            capture_output=True, text=True,
        )
        assert p2.returncode == 0, p2.stderr
        assert "python" in p2.stdout
        assert "python, django" in p2.stdout

        # remove
        p3 = subprocess.run(
            runner_cmd + ["interests", "remove", "python", "--data-dir", dd],
            capture_output=True, text=True,
        )
        assert p3.returncode == 0, p3.stderr
        assert "Removed interest 'python'" in p3.stdout

        # remove again -> not found, exit 1
        p4 = subprocess.run(
            runner_cmd + ["interests", "remove", "python", "--data-dir", dd],
            capture_output=True, text=True,
        )
        assert p4.returncode == 1
        assert "not found" in p4.stdout

    def test_cli_help_lists_interests_group(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "--help"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "interests" in proc.stdout
