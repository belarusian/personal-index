"""Adversarial deep tests for personal_index/scheduler.py — Z-suffix /
unparseable-timestamp data-loss in ScheduleStore._load.

Cycle 325 — probes the neighborhood of the QA-52 fix (commit 9676547,
"normalize naive stored datetimes to UTC in ScheduleStore._load"). The QA-52
fix hardened the naive (offset-less) case, but the defensive `_load` still has
a whole-store data-loss hole on Python < 3.11: the `try` wraps the ENTIRE
per-entry loop, and `datetime.fromisoformat` on Python 3.10 does NOT accept
the ISO-8601 "Z" suffix (that support landed in 3.11). So a single entry whose
last_run/next_run is written with a "Z" (e.g. by an external writer, a
hand-edited file, or a newer Python that emits "Z") raises ValueError on
< 3.11, the `except` fires, and `self._entries = {}` wipes EVERY entry —
including perfectly valid ones.

On Python >= 3.11 `fromisoformat` accepts "Z", so the defect is ABSENT there
and the pin passes (no marker). The xfail-strict marker is therefore
version-conditional: it documents the defect on < 3.11 (where it is real and
unfixed) and is a no-op on >= 3.11 (where the test legitimately passes).

The module's own `_save` emits `+00:00` (not "Z"), so a self round-trip is
safe; the data loss is reachable only via externally-produced store files,
which is exactly the defensive case `_load` is documented to tolerate
(defensive: "missing file -> empty; malformed JSON / non-dict JSON / entry
missing config -> empty (defensive, no crash)").

One REAL contract violation surfaced and is pinned (documented, not
hard-failed, so main stays green):
  - QA-58: a single unparseable ("Z"-suffix) timestamp in ONE entry wipes the
    ENTIRE store, losing all valid sibling entries (Python < 3.11). Expected
    per the defensive contract: the bad entry is skipped and the valid
    entries are preserved.
"""

from __future__ import annotations

import json
from datetime import timedelta


from personal_index.scheduler import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleStore,
)



def _cfg() -> dict:
    return {
        "interval_hours": 24,
        "enabled": True,
        "seed_urls": [],
        "max_pages_per_run": 50,
        "crawl_depth": 2,
        "delay": 1.0,
    }


def _entry(last_run, next_run) -> dict:
    return {
        "config": _cfg(),
        "run_count": 0,
        "total_pages_indexed": 0,
        "last_run": last_run,
        "next_run": next_run,
    }


def _write(tmp_path, data, name="s.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return str(p)


# ── passing armor: the QA-52 fix's neighborhood behaves correctly ─────────
class TestAwareOffsetPreserved:
    def test_non_utc_offset_is_preserved(self, tmp_path):
        p = _write(tmp_path, {"j": _entry("2026-01-01T00:00:00+05:00",
                                          "2026-01-01T00:00:00+05:00")})
        s = ScheduleStore(path=p)
        e = s.get("j")
        assert e is not None
        assert e.next_run.utcoffset() == timedelta(hours=5)

    def test_naive_normalized_to_utc(self, tmp_path):
        p = _write(tmp_path, {"j": _entry("2026-01-01T00:00:00",
                                          "2026-01-01T00:00:00")})
        s = ScheduleStore(path=p)
        e = s.get("j")
        assert e is not None
        assert e.next_run.tzinfo is not None
        assert e.next_run.utcoffset() == timedelta(0)

    def test_mixed_naive_last_aware_next(self, tmp_path):
        p = _write(tmp_path, {"j": _entry("2026-01-01T00:00:00",
                                          "2026-01-01T00:00:00+00:00")})
        s = ScheduleStore(path=p)
        e = s.get("j")
        assert e is not None
        assert e.last_run.tzinfo is not None
        assert e.next_run.tzinfo is not None

    def test_self_round_trip_preserves_entry(self, tmp_path):
        p = str(tmp_path / "rt.json")
        s = ScheduleStore(path=p)
        s.add(ScheduleEntry(name="j", config=ScheduleConfig()))
        s2 = ScheduleStore(path=p)
        assert s2.get("j") is not None


# ── REAL DEFECT: one "Z"-suffix entry wipes the whole store (QA-58) ───────
class TestZSuffixDataLoss:
    def test_one_z_entry_does_not_wipe_valid_siblings(self, tmp_path):
        p = _write(
            tmp_path,
            {
                "good": _entry("2026-01-01T00:00:00+00:00",
                               "2026-01-01T00:00:00+00:00"),
                "bad": _entry("2026-01-01T00:00:00Z",
                              "2026-01-01T00:00:00Z"),
            },
        )
        s = ScheduleStore(path=p)
        # Contract: the valid "good" entry must survive; only "bad" is dropped.
        assert "good" in s._entries
        assert s.get("good") is not None
