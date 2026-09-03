# TICKET-318: progress.ProgressTracker.elapsed_seconds raises ValueError on a corrupt stored started_at

- Status: OPEN
- Issue: #472
- Module: personal_index/progress.py
- Defect class: (a) unguarded parse — `datetime.fromisoformat(self.started_at)` is called
  on a value that can originate from external, untrusted storage.

## Symptom
`ProgressTracker.elapsed_seconds` (progress.py:85) does:
    if not self.started_at:
        return 0.0
    start = datetime.fromisoformat(self.started_at)
`started_at` is a plain `str | None` field, set verbatim by `ProgressTracker.from_dict`
(progress.py:177), which is fed by `ProgressStore.load_all` (progress.py:263) from a JSON
file on disk. A corrupt/non-ISO `started_at` string therefore makes `elapsed_seconds`
raise `ValueError: Invalid isoformat string`.

## Evidence (verified at runtime, cycle 47)
- `ProgressTracker.from_dict({... "started_at": "not-a-timestamp"}).elapsed_seconds`
  -> `ValueError: Invalid isoformat string: 'not-a-timestamp'`
- Full external path: a store file containing
  `{"op1": {"operation_name":"x","state":"running","total_steps":10,"current_step":2,
  "started_at":"garbage"}}` -> `ProgressStore.load_all()` succeeds (returns 1), then
  `store.get("op1").elapsed_seconds` -> `ValueError: Invalid isoformat string: 'garbage'`.
- `to_dict` (progress.py:168) also calls `self.elapsed_seconds`, so the same corrupt value
  crashes `to_dict` / `save_all` on a load->save round-trip.
No test in tests/test_progress.py exercised a non-ISO `started_at` before this fix.

## Impact
`load_all` is the persistence-recovery path. A single corrupt `started_at` in a persisted
progress file makes any subsequent read of that tracker (`elapsed_seconds`, `to_dict`,
`save_all`) raise, aborting the whole load/save cycle. Same defect family as
TICKET-312/313 (unguarded `datetime.fromisoformat` on corrupt stored timestamps).

## Fix (minimal, additive)
Guard the parse in `elapsed_seconds`: on `ValueError` (or a non-string value) return `0.0`,
matching the existing `if not self.started_at: return 0.0` fallback. No signature or
behavior change for valid timestamps. Adds regression tests pinning the guard (corrupt
string, non-string value, and the load_all external path).
