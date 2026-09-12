# ARCH-37: rate_limiter — `RateLimitConfig` numeric fields are unvalidated; `window_seconds == 0` and `max_requests <= 0` raise `ZeroDivisionError`

Status: IMPLEMENTED #1294@bbc0af9
Component: `personal_index/rate_limiter.py`
Issue: #1104
Refs: ARCH-2 (#983 umbrella)

## Symptom

`RateLimitConfig.__post_init__` does exactly one thing: if `burst_size is
None`, set `burst_size = max_requests`. It performs **no bounds check** on
`max_requests`, `window_seconds`, or `burst_size`. Two degenerate configs
crash the module:

- **`window_seconds == 0`** → `TokenBucket.__init__` computes
  `_refill_rate = config.max_requests / config.window_seconds` and raises
  `ZeroDivisionError` at construction time — i.e. on the first
  `can_request` / `get_status` / `get_wait_time` call that lazily creates the
  domain's bucket.
- **`max_requests <= 0`** → `_refill_rate == 0` (or negative). Construction
  succeeds, but the first `wait_time()` (`(1.0 - _tokens) / _refill_rate`) or
  `status()` (`(_burst_size - _tokens) / _refill_rate`) call raises
  `ZeroDivisionError`. With `max_requests == 0` the bucket also starts at
  `_tokens = 0.0`, so `acquire()` is permanently `False` and
  `wait_for_request()` spins until `timeout` before returning `False`.

A negative `window_seconds` is equally unguarded: it makes `_refill_rate`
negative, so `_refill()` *decreases* `_tokens` over time (the budget drains
instead of refilling) and `wait_time()` / `status()` compute a negative wait
and a `reset_at` in the past.

This is the single most important hole in the module: the config is the only
input surface, and the two most natural "tight limit" values (`window_seconds
== 0` for "no window", `max_requests == 0` for "block all") are exactly the
ones that crash rather than degrade.

## Public contract (target)

`RateLimitConfig.__post_init__` must validate the numeric fields and fail
fast at construction with a clear `ValueError` (not a `ZeroDivisionError`
deep in the request path):

- `max_requests >= 1` (else `ValueError`).
- `window_seconds > 0` (else `ValueError`).
- `burst_size >= 1` (else `ValueError`; after the existing
  `burst_size is None -> max_requests` normalization).

Concretely:

- `RateLimitConfig(max_requests=0)` raises `ValueError`.
- `RateLimitConfig(window_seconds=0)` raises `ValueError`.
- `RateLimitConfig(burst_size=0)` raises `ValueError`.
- `RateLimitConfig(max_requests=-1)` raises `ValueError`.
- `RateLimitConfig(window_seconds=-5)` raises `ValueError`.
- A valid config (e.g. the default, or `max_requests=5, window_seconds=10`)
  still constructs, and `burst_size is None` still normalizes to
  `max_requests`.

## Acceptance criteria

1. `RateLimitConfig(max_requests=0)` raises `ValueError` (message names the
   offending field / constraint).
2. `RateLimitConfig(window_seconds=0)` raises `ValueError`.
3. `RateLimitConfig(burst_size=0)` raises `ValueError`.
4. `RateLimitConfig(max_requests=-1)` raises `ValueError`.
5. `RateLimitConfig(window_seconds=-5)` raises `ValueError`.
6. `RateLimitConfig()` (defaults) and `RateLimitConfig(max_requests=5,
   window_seconds=10)` construct successfully; `burst_size is None` still
   normalizes to `max_requests`.
7. After the fix, `TokenBucket(RateLimitConfig(max_requests=5,
   window_seconds=10))` constructs and `acquire()` / `wait_time()` /
   `status()` run without `ZeroDivisionError`.

## Pinning tests to add (implementer)

- `test_config_zero_window_raises`: `pytest.raises(ValueError)` on
  `RateLimitConfig(window_seconds=0)` (pins the `window_seconds > 0` guard).
- `test_config_zero_max_requests_raises`: `pytest.raises(ValueError)` on
  `RateLimitConfig(max_requests=0)` (pins the `max_requests >= 1` guard).
- `test_config_zero_burst_raises`: `pytest.raises(ValueError)` on
  `RateLimitConfig(burst_size=0)` (pins the `burst_size >= 1` guard).
- `test_config_negative_window_raises`: `pytest.raises(ValueError)` on
  `RateLimitConfig(window_seconds=-5)` (pins the negative-window guard).
- `test_config_negative_max_requests_raises`: `pytest.raises(ValueError)` on
  `RateLimitConfig(max_requests=-1)` (pins the negative-max guard).
- `test_config_valid_constructs`: `RateLimitConfig()` and
  `RateLimitConfig(max_requests=5, window_seconds=10)` construct; assert
  `RateLimitConfig().burst_size == 10` (the `None -> max_requests`
  normalization still holds — the normal-case pin alongside the guard paths).

## Docs

`docs/rate-limiter.md` (authored this cycle) documents the current behavior
and lists this as the primary contract hole. Update the `RateLimitConfig`
entry and the "Contract Holes" section in the **same PR** that implements the
fix, so the page reflects the validated-config semantics.
