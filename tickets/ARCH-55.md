# ARCH-55 — content_health: `HealthIssue`/`HealthCheckResult` need `from_dict` (and `HealthReport` needs `to_dict`) so a serialized report can be reloaded

Status: OPEN
Component: `personal_index/content_health.py` — `HealthIssue`, `HealthCheckResult`, `HealthReport`
Umbrella: ARCH-2 (#983)
Issue: #1170
Docs: `docs/content-health.md` (Contract Holes)

## Problem
The persistence path for content health is **one-way**. `HealthIssue.to_dict()`
and `HealthCheckResult.to_dict()` exist and serialize cleanly (enums emitted as
their `.value` strings), but:

- `HealthIssue` has **no `from_dict`** — a serialized issue dict cannot be
  reloaded into a `HealthIssue` (the `severity` string is not mapped back to
  `IssueSeverity`).
- `HealthCheckResult` has **no `from_dict`** — a serialized result dict cannot
  be reloaded into a `HealthCheckResult` (the `status` string is not mapped
  back to `HealthStatus`, and the nested `issues` list is not rebuilt).
- `HealthReport` has **no `to_dict` at all** — the aggregate report (counts,
  `overall_score`, `total_issues`) is not directly serializable; only its
  per-item `results` are.

Consequence: any consumer that wants to persist a health report (e.g. to disk
or a cache) and later re-score, re-render, or re-aggregate it must hand-roll
the reverse mapping for `severity`/`status` enums and the nested `issues`
list, and has no path to serialize the report-level aggregates. This is the
same class of hole as ARCH-54 (lossy round-trip) but in the **missing reverse
direction**: the forward `to_dict` path exists, the return path does not.

## Public contract (target)
- `HealthIssue.from_dict(cls, data: dict) -> HealthIssue` — reads `url`,
  `title`, `issue_type`, `severity`, `message`, `suggestion` (default `""`);
  maps `severity` (a string) back to `IssueSeverity` via
  `IssueSeverity(data["severity"])`.
- `HealthCheckResult.from_dict(cls, data: dict) -> HealthCheckResult` — reads
  `url`, `title`, `status`, `issues` (default `[]`), `score` (default `100.0`),
  `checks_passed` (default `0`), `checks_total` (default `0`); maps `status`
  back to `HealthStatus` via `HealthStatus(data["status"])` and rebuilds each
  `issues` entry via `HealthIssue.from_dict`.
- `HealthReport.to_dict() -> dict` — serializes all eight fields; each
  `results` entry via `HealthCheckResult.to_dict`.
- `HealthReport.from_dict(cls, data: dict) -> HealthReport` — reads all eight
  fields; rebuilds each `results` entry via `HealthCheckResult.from_dict`.

After the change, `HealthCheckResult.from_dict(r.to_dict())` and
`HealthReport.from_dict(report.to_dict())` are lossless round-trips: enums are
restored to their members and the nested `issues` list is rebuilt.

## Behavior
- Round-trip of a `HealthCheckResult` with a non-empty `issues` list: the
  reloaded result has the same `status` (enum member), the same `issues`
  (each with `severity` restored to its `IssueSeverity` member), and the same
  `score` / `checks_passed` / `checks_total`.
- Round-trip of a `HealthCheckResult` with an empty `issues` list (HEALTHY
  item): unchanged.
- Round-trip of a `HealthReport` built by `check_all`: the reloaded report has
  the same counts, `overall_score`, `total_issues`, and `results`.
- `from_dict` on a dict that LACKS optional keys (`suggestion`, `issues`,
  `score`, `checks_passed`, `checks_total`): applies the documented defaults
  (backward-compatible; no error).

## Guard inputs
- `HealthCheckResult.from_dict` on a minimal dict (`url`, `title`, `status`
  only) — defaults applied (`issues == []`, `score == 100.0`,
  `checks_passed == 0`, `checks_total == 0`).
- `HealthIssue.from_dict` on a dict lacking `suggestion` — `suggestion == ""`.
- `HealthReport.from_dict` on a dict with an empty `results` list —
  `total_items == 0`, `results == []`.
- Round-trip of a result whose `status` is `UNHEALTHY` (HIGH issue present) —
  the enum member is restored, not the string.

## Acceptance criteria
1. For a `HealthCheckResult` produced by `check_item` with at least one issue,
   `HealthCheckResult.from_dict(r.to_dict())` has `status == r.status` (enum
   member), `len(issues) == len(r.issues)`, and each reloaded issue has
   `severity == original.severity` (enum member).
2. `HealthCheckResult.from_dict` on a dict missing `issues`/`score`/
   `checks_passed`/`checks_total` does not raise and yields the documented
   defaults.
3. `HealthReport.to_dict()` contains the keys `total_items`, `healthy_count`,
   `warning_count`, `unhealthy_count`, `unknown_count`, `total_issues`,
   `results`, `overall_score`.
4. For a `HealthReport` produced by `check_all`,
   `HealthReport.from_dict(report.to_dict())` has the same counts,
   `overall_score`, `total_issues`, and `len(results)`.
5. Existing `to_dict` behavior on `HealthIssue` / `HealthCheckResult` is
   unchanged (existing tests still pass).

## Pinning tests to add
- `test_health_check_result_roundtrip_preserves_status_and_issues`: build a
  result via `ContentHealthChecker().check_item(url="http://x", title="ab",
  content="")` (produces `missing_title` + `low_content`, status WARNING),
  round-trip via `to_dict`/`from_dict`, assert `status` is the same enum
  member and each reloaded issue's `severity` is the same enum member.
- `test_health_check_result_from_dict_missing_keys_defaults`: `from_dict` on a
  dict with only `url`/`title`/`status` yields `issues == []`,
  `score == 100.0`, `checks_passed == 0`, `checks_total == 0` (no exception).
- `test_health_report_roundtrip_preserves_aggregates`: build a report via
  `check_all` over a mixed list (one healthy, one unhealthy item), round-trip
  via `to_dict`/`from_dict`, assert `healthy_count`, `unhealthy_count`,
  `total_issues`, `overall_score`, and `len(results)` are all preserved.

## Docs update (same PR)
`docs/content-health.md` — `HealthIssue` / `HealthCheckResult` / `HealthReport`
entries: state that `from_dict` (and `HealthReport.to_dict`) now exist and the
round-trip is lossless (enums restored, nested `issues` rebuilt). Remove/adjust
the Contract-holes bullet for this hole once merged.
