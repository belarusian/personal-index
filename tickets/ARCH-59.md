# ARCH-59 — throttle: `ThrottleRule.rate_per_second` divides by the raw, unguarded `window_seconds` (ZeroDivisionError on `window_seconds==0`), and the probe (`should_throttle`) and the wait path (`wait_if_needed`) diverge on the same rule

Status: OPEN
Component: `personal_index/throttle.py` — `ThrottleRule.rate_per_second`, `ThrottleRule.__init__`/`__post_init__`, `ThrottleManager.wait_if_needed`, `ThrottleManager.should_throttle`
Umbrella: ARCH-2 (#983)
Related: QA-13 (issue #1175) — same `rate_per_second` ZeroDivisionError, plus the `_extract_domain` non-normalized-key hole (out of scope here)
Docs: `docs/throttle.md` (Contract Holes)

## Problem
`ThrottleRule.rate_per_second` is a raw division with no guard:

    @property
    def rate_per_second(self) -> float:
        return self.max_requests / self.window_seconds

So `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` raises
`ZeroDivisionError: float division by zero`.

The crash is **path-dependent**, which is the real contract hole:

- `should_throttle(url)` (throttle.py:62-77) **never** dereferences
  `rate_per_second` — it only prunes `request_times` and compares
  `len(request_times) >= max_requests`. So the probe is **safe** under a
  zero-window rule.
- `wait_if_needed(url)` (throttle.py:82-107) dereferences `rate_per_second`
  **only** inside `if state.last_request is not None` (throttle.py:90-93):

        if state.last_request is not None:
            elapsed = now - state.last_request
            min_wait = 1.0 / rule.rate_per_second if rule.rate_per_second > 0 else rule.min_delay

  `state.last_request` is `None` before the first request and set by
  `_record_request` after it. So the **1st** `wait_if_needed` call to a domain
  returns `0.0` (safe), but the **2nd+** call to the same domain with a
  zero-window rule **raises `ZeroDivisionError`**.

The `if rule.rate_per_second > 0` guard is itself the crash point: it evaluates
the property (the division) *before* the comparison, so the guard cannot
protect against the very condition it is meant to test.

Net effect: the probe and the wait path **diverge on the same rule** — a caller
who probes with `should_throttle` sees a clean `True`/`False`, while a caller
who waits with `wait_if_needed` crashes on the second request. This is the same
class as the `rate_limiter` unvalidated-config hole (ARCH-37) and is already
documented in QA-13 (issue #1175).

## Public contract (target)
Make `rate_per_second` and `wait_if_needed` agree: **one rule, one behavior, no
path raises on a degenerate window.** Pick ONE of the two options below and
state it in the docstrings so the probe and the wait path cannot diverge:

Preferred option (document it in the docstrings):
1. **Guard the division with a finite fallback** — make `rate_per_second`
   return a finite value when `window_seconds <= 0` (e.g. `0.0` when
   `window_seconds <= 0`, so the existing `if rule.rate_per_second > 0 else
   rule.min_delay` branch in `wait_if_needed` falls through to `min_delay`).
   Then `ThrottleRule(window_seconds=0).rate_per_second` does **not** raise,
   and `wait_if_needed` uses `min_delay` as the inter-request floor. This is
   the least invasive and keeps the probe/wait paths consistent (both treat a
   zero window as "no rate budget, fall back to min_delay").
2. **Reject the config up front** — validate `window_seconds > 0` in
   `ThrottleRule.__init__`/`__post_init__` and raise `ValueError` for
   `window_seconds <= 0`. Then `rate_per_second` can never divide by zero
   because no zero-window rule can be constructed. This is a breaking change
   for the currently-constructible (but crash-on-use) zero-window rule, so it
   is the less-preferred option.

Regardless of option, `should_throttle` and `wait_if_needed` must agree on the
throttle decision for the same rule (the probe must not report a budget the
wait path cannot honor, and vice versa).

## Behavior
- `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` → does
  **not** raise (option 1: returns a finite fallback such as `0.0`; option 2:
  the constructor raises `ValueError` instead, so the property is never reached).
- Two consecutive `wait_if_needed` calls on one domain with a zero-window rule
  → neither raises (option 1: the 2nd+ call falls through to `min_delay`;
  option 2: the rule cannot be constructed, so the call is unreachable).
- `should_throttle` and `wait_if_needed` agree on the throttle decision for the
  same rule (a domain at/over budget is throttled by both; a domain under
  budget is not throttled by either).
- Normal path unchanged: `ThrottleRule(max_requests=10, window_seconds=60).rate_per_second`
  → `10/60 ≈ 0.1667`.

## Guard inputs
- `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` → no raise
  (option 1) / constructor `ValueError` (option 2).
- `ThrottleRule(max_requests=10, window_seconds=-5).rate_per_second` → no raise
  (option 1) / constructor `ValueError` (option 2).
- 1st `wait_if_needed` on a fresh domain with a zero-window rule → `0.0` (safe,
  unchanged).
- 2nd `wait_if_needed` on the same domain with a zero-window rule → no raise
  (option 1: waits at most `min_delay`; option 2: unreachable).
- `should_throttle` on a domain at `max_requests` within the window → `True`
  (probe behavior unchanged).

## Acceptance criteria
1. `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` does
   **not** raise `ZeroDivisionError` (option 1), OR `ThrottleRule(
   window_seconds=0)` raises `ValueError` in the constructor (option 2) — pick
   one and pin it.
2. Two consecutive `wait_if_needed` calls on one domain with a zero-window rule
   do **not** raise.
3. `should_throttle` and `wait_if_needed` agree on the throttle decision for
   the same rule: a domain at/over budget is throttled by both; a domain under
   budget is not throttled by either.
4. Normal path unchanged: `ThrottleRule(max_requests=10, window_seconds=60).rate_per_second`
   is `10/60`.

## Pinning tests to add
- `test_throttle_rule_rate_per_second_zero_window_no_raise`:
  `ThrottleRule(max_requests=10, window_seconds=0).rate_per_second` does not
  raise (option 1) — or `pytest.raises(ValueError)` on construction (option 2).
- `test_throttle_rule_rate_per_second_negative_window_no_raise`:
  `ThrottleRule(max_requests=10, window_seconds=-5).rate_per_second` does not
  raise (option 1) — or `pytest.raises(ValueError)` on construction (option 2).
- `test_wait_if_needed_two_calls_zero_window_no_raise`: two consecutive
  `wait_if_needed` calls on one domain with a zero-window rule do not raise.
- `test_should_throttle_and_wait_agree`: for a domain at/over budget, both
  `should_throttle` and `wait_if_needed` report throttle; for a domain under
  budget, neither does.
- `test_throttle_rule_rate_per_second_normal_unchanged`:
  `ThrottleRule(max_requests=10, window_seconds=60).rate_per_second == 10/60`.

## Docs update (same PR)
`docs/throttle.md` — the Contract Holes section documents this hole; after the
fix, update it to state the new consistent contract (either "rate_per_second
returns a finite fallback for `window_seconds <= 0`" or "the constructor
rejects `window_seconds <= 0` with `ValueError`"), and note that the probe and
the wait path now agree. Remove/adjust the Contract-holes bullet for this hole
once merged, and keep the `_extract_domain` non-normalized-key note (QA-13).
