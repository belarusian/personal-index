# ARCH-64 — text_utils: `read_time_minutes` must guard the raw `wpm` divisor (`wpm <= 0 -> 0`; positive -> `ceil(count/wpm)`)

Status: OPEN
Component: `personal_index/text_utils.py` — `read_time_minutes` (lines 283-294)
Umbrella: ARCH-2 (#983)
Issue: #1193
Binding decision for: ARCH-60 (issue #1193) — resolves its open two-option question with a single binding rule
Class: guard-the-raw-divisor — ARCH-58 (pagination `per_page`), ARCH-59 (throttle `window_seconds`)
Docs: `docs/CONTRACTS.md` (Divisor guard rule, this design PR); `docs/text-utils.md` (component entry, implementer's fix PR)

## Problem
`read_time_minutes` divides by the raw, unguarded `wpm`:

    def read_time_minutes(text: str, wpm: int = 200) -> int:
        words = count_words(text)
        return max(1, round(words / wpm))

Two failures (verified empirically, ARCH-60 / issue #1193):

- **`wpm == 0` -> `ZeroDivisionError: division by zero`.**
  `read_time_minutes('word '*300, wpm=0)` raises.
- **`wpm < 0` -> silently returns a bogus `1`.**
  `read_time_minutes('word '*300, wpm=-5)` returns `1`, because
  `round(negative)` is negative and `max(1, negative)` clamps it to `1`. A
  negative reading speed is accepted and produces a bogus "1 minute" answer.

This is the same "guard the raw divisor" class as ARCH-58 (pagination
`per_page`) and ARCH-59 (throttle `window_seconds`): a helper that divides by
a caller-supplied scalar must clamp/short-circuit a non-positive divisor to a
defined safe result instead of raising or returning a silent wrong value.

## Binding decision (resolves ARCH-60's open two-option question)
`read_time_minutes` — and any minutes-from-count/wpm helper — MUST guard the
divisor:

- **`wpm <= 0` -> return `0`** (no division, no exception, no bogus `1`).
- **`wpm > 0` -> `ceil(count / wpm)`** where `count = count_words(text)`.

The guard is stated in the function's contract docstring (part 1, guard
paths) and witnessed by ONE pinning test that asserts the returned int for the
guard inputs ALONGSIDE the normal positive case.

## Public contract (target)
`read_time_minutes(text: str, wpm: int = 200) -> int`:

- **Guard path:** `wpm <= 0` -> returns exactly `0` (short-circuits before any
  division; no `ZeroDivisionError`, no `ValueError`, no bogus `1`).
- **Normal path:** `wpm > 0` -> returns `ceil(count_words(text) / wpm)`.
- **Side effects:** none.

## Worked examples
- `read_time_minutes('word '*300, wpm=0)` -> `0` (guard; no ZeroDivisionError).
- `read_time_minutes('word '*300, wpm=-5)` -> `0` (guard; no bogus `1`).
- `read_time_minutes('word '*1000, wpm=200)` -> `5` (`ceil(1000/200)`).

## Guard inputs
- `wpm == 0` -> `0`.
- `wpm < 0` (e.g. `-5`) -> `0`.
- `wpm > 0` -> `ceil(count/wpm)`.

## Acceptance criteria
1. `read_time_minutes(text, wpm=0)` returns `0` (does NOT raise
   `ZeroDivisionError`).
2. `read_time_minutes(text, wpm=-5)` returns `0` (does NOT return a bogus `1`).
3. `read_time_minutes('word '*1000, wpm=200)` returns `5` (`ceil(1000/200)`).
4. The guard is stated in the contract docstring (part 1) and the positive
   path uses `ceil`, not `round`.

## Pinning tests to add
- `test_read_time_minutes_zero_wpm_returns_zero`:
  `read_time_minutes('word '*300, wpm=0) == 0` (no ZeroDivisionError).
- `test_read_time_minutes_negative_wpm_returns_zero`:
  `read_time_minutes('word '*300, wpm=-5) == 0` (no bogus 1).
- `test_read_time_minutes_positive_wpm_ceil`:
  `read_time_minutes('word '*1000, wpm=200) == 5` (`ceil(1000/200)`).

## Docs update (same PR)
`docs/CONTRACTS.md` — add the **Divisor guard (binding)** rule + a matching
**How to apply** step (this design PR). `docs/text-utils.md` — the
`read_time_minutes` Contract-holes entry is updated by the implementer in the
SAME PR that lands the code fix (state the guard: `wpm <= 0 -> 0`, positive
-> `ceil(count/wpm)`; remove the Contract-holes bullet once merged).

## Class reference
This rule is the single home for the guard-the-raw-divisor class (ARCH-64).
Per-site instances reference it: ARCH-58 (pagination `per_page`), ARCH-59
(throttle `window_seconds`), ARCH-60 (this `read_time_minutes` `wpm` site).
Do NOT re-open ARCH-58/59.
