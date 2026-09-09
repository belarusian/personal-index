# content-health — `personal_index.content_health`

Content health monitoring. Checks the health and quality of content items
passed to `check_item` / `check_all` against configurable rules, flagging
issues such as invalid URLs, missing or oversized titles, low-content items,
missing tags, low scores, and bad HTTP status codes.

Stdlib-only (`collections.abc`, `dataclasses`, `enum`, `typing`). No I/O, no
network, no disk — every check is a pure in-memory predicate over the item's
fields.

## Public API

### `HealthStatus` (Enum)

Per-item health verdict.

| Member | Value |
|--------|-------|
| `HEALTHY` | `"healthy"` |
| `WARNING` | `"warning"` |
| `UNHEALTHY` | `"unhealthy"` |
| `UNKNOWN` | `"unknown"` |

> `UNKNOWN` is **unreachable** from `check_item`: `_determine_status` returns
> only `HEALTHY` / `WARNING` / `UNHEALTHY`. `HealthReport.unknown_count` is
> therefore always `0` for reports built by `check_all`.

### `IssueSeverity` (Enum)

| Member | Value |
|--------|-------|
| `LOW` | `"low"` |
| `MEDIUM` | `"medium"` |
| `HIGH` | `"high"` |
| `CRITICAL` | `"critical"` |

> `CRITICAL` is **unreachable** from `check_item`: no check emits a
> `CRITICAL` issue. The `CRITICAL` branch in `_determine_status` is dead for
> checker-produced issues (it would matter only for a hand-built
> `HealthIssue`).

### `HealthIssue` (dataclass)

One issue found in a content item.

| Field | Type | Default |
|-------|------|---------|
| `url` | `str` | — |
| `title` | `str` | — |
| `issue_type` | `str` | — |
| `severity` | `IssueSeverity` | — |
| `message` | `str` | — |
| `suggestion` | `str` | `""` |

`issue_type` values produced by the checker: `invalid_url`, `missing_title`,
`title_too_long`, `low_content`, `bad_status`, `missing_tags`, `low_score`.

- `to_dict() -> dict[str, Any]` — serializes all six fields; `severity` is
  emitted as its `.value` string (e.g. `"high"`), not the enum member.

> **No `from_dict`.** There is no reverse constructor — a serialized issue
> cannot be reloaded into a `HealthIssue`. See Contract Holes.

### `HealthCheckResult` (dataclass)

Result of a health check on one content item.

| Field | Type | Default |
|-------|------|---------|
| `url` | `str` | — |
| `title` | `str` | — |
| `status` | `HealthStatus` | — |
| `issues` | `list[HealthIssue]` | `field(default_factory=list)` |
| `score` | `float` | `100.0` |
| `checks_passed` | `int` | `0` |
| `checks_total` | `int` | `0` |

- `to_dict() -> dict[str, Any]` — serializes all seven fields; `status` is
  emitted as its `.value` string and each `issues` entry via
  `HealthIssue.to_dict`.

> **No `from_dict`.** A serialized result cannot be reloaded into a
> `HealthCheckResult`. See Contract Holes.

### `HealthReport` (dataclass)

Aggregates results from checked content items.

| Field | Type | Default |
|-------|------|---------|
| `total_items` | `int` | `0` |
| `healthy_count` | `int` | `0` |
| `warning_count` | `int` | `0` |
| `unhealthy_count` | `int` | `0` |
| `unknown_count` | `int` | `0` |
| `total_issues` | `int` | `0` |
| `results` | `list[HealthCheckResult]` | `field(default_factory=list)` |
| `overall_score` | `float` | `100.0` |

- `health_percentage` (property) -> `float` — `100.0` when `total_items == 0`,
  else `(healthy_count / total_items) * 100`.
- `summary() -> str` — eight lines joined by `\n`, in order:
  `Content Health Report`, 40 `=` signs, `Total items: {total_items}`,
  `Healthy: {healthy_count}`, `Warnings: {warning_count}`,
  `Unhealthy: {unhealthy_count}`, `Overall score: {overall_score:.1f}/100`,
  `Health percentage: {health_percentage:.1f}%`.

> `HealthReport` has **no `to_dict` / `from_dict`** at all — the aggregate
> report is not directly serializable; only its per-item `results` are.

### `ContentHealthCheck` (dataclass)

Configuration for the checks.

| Field | Type | Default |
|-------|------|---------|
| `min_content_length` | `int` | `50` |
| `min_title_length` | `int` | `3` |
| `max_title_length` | `int` | `200` |
| `require_tags` | `bool` | `False` |
| `min_tags` | `int` | `1` |
| `require_score` | `bool` | `False` |
| `min_score` | `float` | `0.0` |

### `ContentHealthChecker`

`__init__(self, config: ContentHealthCheck | None = None)` — stores
`config or ContentHealthCheck()`.

#### `check_item(url, title, content="", tags=None, score=0.0, status_code=200) -> HealthCheckResult`

Runs up to **seven** checks in order, appending one `HealthIssue` per failure
and accumulating `checks_total` (`ct`) / `checks_passed` (`cp`):

| # | Check | Passes when | On failure: `issue_type` / severity |
|---|-------|-------------|-------------------------------------|
| 1 | url | `url` truthy and `len(url) > 5` | `invalid_url` / HIGH |
| 2 | title presence | `title` truthy and `len(title) >= min_title_length` | `missing_title` / MEDIUM |
| 3 | title length | `len(title) <= max_title_length` | `title_too_long` / LOW |
| 4 | content length | `len(content) >= min_content_length` | `low_content` / MEDIUM |
| 5 | status code | `200 <= status_code < 400` | `bad_status` / HIGH |
| 6 | tags | **only when `require_tags`**; `tags` truthy and `len(tags) >= min_tags` | `missing_tags` / LOW |
| 7 | score | **only when `require_score`**; `score >= min_score` | `low_score` / LOW |

Checks 6 and 7 are **skipped entirely** (they do not increment `ct`) when the
corresponding `require_*` flag is off, so `checks_total` is `5` by default and
`7` when both flags are on.

- `status` is `UNHEALTHY` if any issue is HIGH or CRITICAL, `WARNING` if any
  issue is MEDIUM or any issue at all, else `HEALTHY`.
- `score` is `checks_passed / checks_total * 100`, or `0.0` when no check ran
  (`checks_total == 0`).

#### `check_all(items: list[dict[str, Any]]) -> HealthReport`

Maps each item dict through `check_item` via `_check_from_dict`, which reads
`item.get(key, default)` with defaults `url`/`title`/`content` -> `""`,
`tags` -> `[]`, `score` -> `0.0`, `status_code` -> `200`. Returns a
`HealthReport` (via `_build_report`) where:

- `healthy_count` / `warning_count` / `unhealthy_count` / `unknown_count`
  count the per-item statuses (`unknown_count` is always `0`);
- `total_issues` sums the per-item issue counts;
- `overall_score` is the **mean** of the per-item scores, or `100.0` when
  `items` is empty.

## Contract Holes

**Single most important hole — the persistence round-trip is one-way.**
`HealthIssue.to_dict` and `HealthCheckResult.to_dict` exist, but **neither
class has a `from_dict`**, and `HealthReport` has no `to_dict` at all. A
health report can be serialized to dicts but can never be reloaded: the
`status` / `severity` strings are not mapped back to their enums, and the
aggregate report has no serialization path. Any consumer that wants to persist
a report and later re-score or re-render it must hand-roll the reverse
mapping. This is the same class of hole as ARCH-54 (lossy round-trip) but in
the *missing reverse direction*: the forward path exists, the return path does
not. See `tickets/ARCH-55.md`.

Secondary (documented here, not ticketed): `HealthStatus.UNKNOWN` and
`IssueSeverity.CRITICAL` are unreachable from `check_item`, so
`HealthReport.unknown_count` is always `0` and the CRITICAL branch of
`_determine_status` is dead for checker-produced issues.
