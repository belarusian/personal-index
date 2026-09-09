# throttle — `personal_index.throttle`

Request throttling with per-domain rate limiting. A `ThrottleManager` keeps one
`ThrottleState` per domain and, for each request URL, decides whether to wait
(`wait_if_needed`) or simply reports whether the budget is exhausted
(`should_throttle`). The per-domain budget is a `ThrottleRule` (a sliding-window
counter: at most `max_requests` requests within `window_seconds`).

Stdlib-only (`logging`, `time`, `dataclasses`, `urllib.parse`). The only
side-effecting call is `time.sleep(wait_time)` inside `wait_if_needed` when a
wait is computed; `should_throttle` is a pure probe (it does **not** record the
request).

## Public API

### `ThrottleRule` (dataclass)

The per-domain rate-limit budget.

| Field | Type | Default |
|-------|------|---------|
| `max_requests` | `int` | `10` |
| `window_seconds` | `float` | `60.0` |
| `min_delay` | `float` | `0.5` |

- `rate_per_second` (property) — `max_requests / window_seconds`. **Division
  path:** this is a raw division with **no guard on `window_seconds == 0`** —
  a rule built with `window_seconds=0` raises `ZeroDivisionError` here. See the
  Contract Holes section for why the crash is path-dependent (the probe never
  touches this property; only the wait path does).

### `ThrottleState` (dataclass)

Mutable per-domain throttle state.

| Field | Type | Default |
|-------|------|---------|
| `request_times` | `list[float]` | `[]` |
| `last_request` | `float \| None` | `None` |
| `total_requests` | `int` | `0` |
| `total_wait_time` | `float` | `0.0` |

`request_times` holds the timestamps of requests still inside the current
window (pruned on each probe/wait). `last_request` is the timestamp of the most
recent recorded request, or `None` before the first request.

### `ThrottleManager`

`__init__(self, default_rule: ThrottleRule | None = None)` — stores
`self._rules` (per-domain overrides), `self._states` (per-domain state), and
`self._default_rule = default_rule or ThrottleRule()`.

- `set_rule(domain: str, rule: ThrottleRule) -> None` — set the rule for a
  specific domain (overrides the default for that domain only).
- `get_rule(domain: str) -> ThrottleRule` — the per-domain rule if set, else
  the default rule.
- `should_throttle(url: str) -> bool` — **probe only.** Extracts the domain,
  prunes `request_times` older than `now - window_seconds`, and returns
  `len(request_times) >= max_requests`. Does **not** record the request and
  does **not** dereference `rate_per_second`, so it is safe even for a
  zero-window rule.
- `wait_if_needed(url: str) -> float` — the wait path. Extracts the domain and
  computes a wait time from two sources:
  1. **Inter-request delay:** *only when `state.last_request is not None`*
     (i.e. the 2nd+ request to that domain), it computes
     `min_wait = 1.0 / rule.rate_per_second if rule.rate_per_second > 0 else
     rule.min_delay` and waits `min_wait - elapsed` if the elapsed time since
     the last request is shorter. **This is the only place `rate_per_second`
     is dereferenced** — and the `if rule.rate_per_second > 0` guard evaluates
     the property *before* the comparison, so a zero-window rule raises
     `ZeroDivisionError` here on the 2nd+ request.
  2. **Window budget:** if `should_throttle(url)` is true, it waits until the
     oldest in-window request leaves the window
     (`(oldest + window_seconds) - now`), floored by `min_delay`.
  If the computed `wait_time > 0` it calls `time.sleep(wait_time)` and adds it
  to `state.total_wait_time`. It then records the request (see below) and
  returns the wait time in seconds (possibly `0.0`).
- `_record_request(domain, state)` (private) — appends `now` to
  `request_times`, sets `last_request = now`, and increments `total_requests`.
  Called by `wait_if_needed` (not by `should_throttle`).
- `_extract_domain(url: str) -> str` (private) — `urlparse(url).netloc or url`.
  **Not a normalized domain:** it is the raw netloc, so hostname case, port, and
  userinfo are all part of the key (see the Contract Holes section).
- `get_stats(domain: str | None = None) -> dict` — with a domain: per-domain
  `total_requests`, `total_wait_time` and the rule fields (or just
  `total_requests` if the domain is untracked). Without a domain: aggregate
  `domains_tracked`, `total_requests`, `total_wait_time` across all tracked
  domains.
- `reset(domain: str | None = None) -> None` — clear the state for one domain,
  or all domains when `domain` is `None`.

## Contract Holes

- **`rate_per_second` ZeroDivisionError on `window_seconds == 0` (ARCH-59).**
  `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` raises
  `ZeroDivisionError` (raw `max_requests / window_seconds`, no guard). The
  crash is **path-dependent**: `should_throttle` never dereferences the
  property, so the probe is safe under a zero-window rule; `wait_if_needed`
  dereferences it only inside `if state.last_request is not None`, so the
  **1st** request to a domain returns `0.0` (safe) but the **2nd+** request
  raises. The `if rule.rate_per_second > 0` guard is itself the crash point —
  it evaluates the property before the comparison. The probe and the wait path
  can therefore diverge on the same rule. This is the same class as the
  `rate_limiter` unvalidated-config hole (ARCH-37) and is already documented in
  QA-13 (issue #1175).
- **`_extract_domain` is not a true domain extractor (QA-13, issue #1175).**
  The key is the raw `urlparse(url).netloc`, so `EXAMPLE.com` vs `example.com`
  (case), `example.com:8080` vs `example.com` (port), and
  `user:pass@example.com` (userinfo) all map to **different** throttle buckets
  even though they are the same DNS domain. A crawler can bypass the per-domain
  rate limit by varying the hostname form. (Out of scope for ARCH-59; tracked
  under QA-13.)
