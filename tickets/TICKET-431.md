# TICKET-431: content_monitor.health.HealthChecker.check doc-drift (class b)

- File: personal_index/content_monitor/health.py
- Function: HealthChecker.check (lines 53-74)
- Symptom: blanket docstring ("Run all health checks on content items." /
  "HealthStatus with check results.") that does not enumerate the three
  sub-checks it runs, how `healthy` and `score` are derived, or the returned
  HealthStatus fields.
- Evidence:
  - docstring lines 54-60: only "Run all health checks on content items." and
    "HealthStatus with check results." - no enumeration of sub-checks.
  - body lines 62-74: appends `_check_item_count`, `_check_scores`,
    `_check_duplicates`; `healthy = all(c.healthy for c in checks)`;
    `score = sum(1 for c in checks if c.healthy) / len(checks) if checks else 0.0`;
    returns HealthStatus(healthy, checks, score=round(score, 4)).
- Minimal additive fix: reword the docstring to enumerate the three checks
  (item_count vs min_items; scores - every item has an int/float score or the
  list is empty; duplicates - unique count of str(id)), the `healthy`
  (all-pass) and `score` (fraction healthy, rounded to 4, 0.0 when no checks)
  computation, and the returned HealthStatus fields. Add ONE pinning test
  asserting the returned HealthStatus fields for the normal case (all healthy
  -> healthy True, score 1.0, 3 checks) AND the guard path (empty items ->
  healthy False, score 0.0).
- Status: RESOLVED
- Issue: #700
