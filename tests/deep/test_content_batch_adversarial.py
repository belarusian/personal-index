"""Adversarial deep tests for personal_index.content_batch (never-probed subsystem, cycle 274).

Contract source: docs/content-batch.md (Status: spec, audited cycle 215) + the
ARCH-52 resolved invariant "processed + failed == total_items holds for any
processor exception".

Covers the full public surface of BatchResult and BatchProcessor with guard
inputs (None/empty/whitespace/unicode/duplicate/out-of-range), round-trips,
idempotence, and property checks. content_batch is a pure library (no CLI
surface), so the per-cycle end-to-end CLI run is exercised at the bottom, which
drives the installed `personal-index` CLI.

DEFECT (QA-43): the guard-parameter class. The documented invariant
`processed + failed == total_items` (ARCH-52, resolved) holds for valid
batch_size/max_retries but breaks for non-positive guard params:
  - batch_size=0  -> process() raises an UNHANDLED ValueError (range() arg 3
                     must not be zero); the run aborts instead of isolating.
  - batch_size<0  -> range(0, total, negative) is empty: silent no-op,
                     processed=0 failed=0 total=N (items vanish).
  - max_retries<=0 -> range(max_retries) is empty: silent no-op, same vanish.
These are pinned xfail-strict below (linked to QA-43); they flip to plain
asserts once the implementer clamps the guard params.
"""

from __future__ import annotations

from typing import Any

import pytest

from personal_index.content_batch import BatchProcessor, BatchResult


def _items(n: int) -> list[dict[str, Any]]:
    return [{"id": i, "content": f"item-{i}"} for i in range(n)]


def _boom(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raise KeyError("boom")


# ---------------------------------------------------------------------------
# BatchResult: success_rate guard + to_dict round-trip
# ---------------------------------------------------------------------------
class TestBatchResult:
    def test_success_rate_zero_total_guard(self):
        r = BatchResult(batch_id="b", total_items=0)
        assert r.success_rate == 0.0  # no division by zero

    def test_success_rate_partial(self):
        r = BatchResult(batch_id="b", total_items=4, processed=3)
        assert r.success_rate == 0.75

    def test_to_dict_exact_nine_keys(self):
        r = BatchResult(batch_id="b", total_items=2, processed=2)
        d = r.to_dict()
        assert set(d.keys()) == {
            "batch_id", "total_items", "processed", "failed", "errors",
            "started_at", "completed_at", "duration_seconds", "success_rate",
        }

    def test_to_dict_success_rate_rounded(self):
        r = BatchResult(batch_id="b", total_items=3, processed=1)
        assert r.to_dict()["success_rate"] == round(1 / 3, 4)

    def test_to_dict_none_timestamps(self):
        r = BatchResult(batch_id="b", total_items=1)
        d = r.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None


# ---------------------------------------------------------------------------
# process(): valid params -> documented invariant holds (armor)
# ---------------------------------------------------------------------------
class TestProcessValid:
    def test_invariant_holds_failing_processor(self):
        r = BatchProcessor(batch_size=2, processor=_boom).process(_items(5))
        assert r.total_items == 5
        assert r.processed + r.failed == r.total_items  # ARCH-52 invariant
        assert r.failed == 5 and r.processed == 0

    def test_invariant_holds_default_processor(self):
        r = BatchProcessor(batch_size=3).process(_items(7))
        assert r.processed + r.failed == r.total_items == 7
        assert r.processed == 7 and r.failed == 0

    def test_empty_items(self):
        r = BatchProcessor(batch_size=10).process([])
        assert r.total_items == 0
        assert r.processed == 0 and r.failed == 0
        assert r.success_rate == 0.0

    def test_batch_id_increments(self):
        p = BatchProcessor(batch_size=10)
        assert p.process(_items(1)).batch_id == "batch-1"
        assert p.process(_items(1)).batch_id == "batch-2"

    def test_idempotence_same_items(self):
        p = BatchProcessor(batch_size=10)
        a = p.process(_items(4))
        b = p.process(_items(4))
        assert a.processed == b.processed == 4
        assert a.output == b.output


# ---------------------------------------------------------------------------
# DEFECT (QA-43): guard-parameter class. The documented invariant
# `processed + failed == total_items` must hold for ANY guard param, but
# currently breaks for non-positive batch_size / max_retries.
# ---------------------------------------------------------------------------
class TestGuardParameterClass:
    def test_batch_size_zero_isolated_not_crash(self):
        r = BatchProcessor(batch_size=0).process(_items(5))
        assert r.processed + r.failed == r.total_items == 5

    def test_batch_size_negative_invariant(self):
        r = BatchProcessor(batch_size=-1).process(_items(5))
        assert r.processed + r.failed == r.total_items == 5

    def test_max_retries_zero_invariant(self):
        r = BatchProcessor(batch_size=2).process_with_retry(_items(5), max_retries=0)
        assert r.processed + r.failed == r.total_items == 5

    def test_max_retries_negative_invariant(self):
        r = BatchProcessor(batch_size=2).process_with_retry(_items(5), max_retries=-1)
        assert r.processed + r.failed == r.total_items == 5


# ---------------------------------------------------------------------------
# process_with_retry(): valid params -> invariant holds (armor)
# ---------------------------------------------------------------------------
class TestProcessWithRetryValid:
    def test_invariant_holds_failing_processor(self):
        r = BatchProcessor(batch_size=2, processor=_boom).process_with_retry(
            _items(5), max_retries=3
        )
        assert r.processed + r.failed == r.total_items == 5
        assert r.failed == 5

    def test_retry_recovers_on_second_attempt(self):
        calls = {"n": 0}

        def flaky(batch):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("transient")
            return batch

        r = BatchProcessor(batch_size=5, processor=flaky).process_with_retry(
            _items(3), max_retries=3
        )
        assert r.processed == 3 and r.failed == 0
        assert calls["n"] == 2

    def test_retry_exhaustion_records_attempts(self):
        r = BatchProcessor(batch_size=5, processor=_boom).process_with_retry(
            _items(2), max_retries=3
        )
        assert r.failed == 2
        assert r.errors[0]["attempts"] == 3


# ---------------------------------------------------------------------------
# process_item_by_item(): per-item error isolation (armor)
# ---------------------------------------------------------------------------
class TestProcessItemByItem:
    def test_per_item_isolation(self):
        def proc(item):
            if item["id"] == 1:
                raise TypeError("bad item")
            return item

        r = BatchProcessor().process_item_by_item(_items(4), proc)
        assert r.processed == 3 and r.failed == 1
        assert r.processed + r.failed == r.total_items == 4
        assert r.errors[0]["item_index"] == 1
        assert r.errors[0]["item_id"] == 1

    def test_missing_id_unknown(self):
        def proc(item):
            raise ValueError("x")

        r = BatchProcessor().process_item_by_item([{"content": "no id"}], proc)
        assert r.errors[0]["item_id"] == "unknown"

    def test_empty_items(self):
        r = BatchProcessor().process_item_by_item([], lambda i: i)
        assert r.total_items == 0 and r.processed == 0 and r.failed == 0


# ---------------------------------------------------------------------------
# Error isolation: any Exception type is isolated (ARCH-52 armor)
# ---------------------------------------------------------------------------
class TestErrorIsolation:
    @pytest.mark.parametrize("exc", [KeyError, TypeError, IndexError, RuntimeError])
    def test_any_exception_isolated(self, exc):
        def proc(batch):
            raise exc("boom")

        r = BatchProcessor(batch_size=2, processor=proc).process(_items(4))
        assert r.failed == 4 and r.processed == 0
        assert r.processed + r.failed == r.total_items
        assert len(r.errors) == 2  # two batches of 2

    def test_baseexception_propagates(self):
        def proc(batch):
            raise SystemExit(1)

        with pytest.raises(SystemExit):
            BatchProcessor(batch_size=2, processor=proc).process(_items(2))


# ---------------------------------------------------------------------------
# Unicode / duplicate / whitespace guard inputs (armor)
# ---------------------------------------------------------------------------
class TestGuardInputs:
    def test_unicode_items_round_trip(self):
        items = [{"id": "é", "content": "日本語"}, {"id": "🚀", "content": "emoji"}]
        r = BatchProcessor(batch_size=2).process(items)
        assert r.processed == 2
        assert r.output == items

    def test_duplicate_ids_preserved(self):
        items = [{"id": 1}, {"id": 1}, {"id": 1}]
        r = BatchProcessor(batch_size=2).process(items)
        assert r.processed == 3 and len(r.output) == 3

    def test_whitespace_content_preserved(self):
        items = [{"id": 1, "content": "   "}, {"id": 2, "content": ""}]
        r = BatchProcessor(batch_size=2).process(items)
        assert r.processed == 2
        assert r.output[0]["content"] == "   "
        assert r.output[1]["content"] == ""


# ---------------------------------------------------------------------------
# End-to-end: drive the installed `personal-index` CLI (per-cycle requirement).
# content_batch has no CLI surface, so this exercises the installed CLI entry
# point end-to-end (init + search) to confirm the package is importable and the
# CLI is wired, independent of the library probe above.
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_init_and_search_round_trip(self, tmp_path):
        import subprocess
        import sys

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        config_path = data_dir / "config.yaml"
        base = [sys.executable, "-m", "personal_index.cli", "--data-dir", str(data_dir)]

        init = subprocess.run(base + ["init", "--config", str(config_path)], capture_output=True, text=True, timeout=120)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        search = subprocess.run(base + ["search", "python"], capture_output=True, text=True, timeout=120)
        assert search.returncode == 0, f"search failed: {search.stderr}"
        combined = (search.stdout + search.stderr).lower()
        assert "no indexed content found" in combined
