# ARCH-60 — text_utils: `read_time_minutes` divides by the raw, unguarded `wpm` (ZeroDivisionError on `wpm==0`, silent bogus `1` on `wpm<0`)

Status: OPEN
Component: `personal_index/text_utils.py` — `read_time_minutes` (lines 283-294)
Umbrella: ARCH-2 (#983)
Issue: #1193
Related: ARCH-59 (throttle `rate_per_second` ZeroDivisionError), ARCH-37 (rate_limiter unvalidated config) — same unvalidated-numeric-input class
Docs: `docs/text-utils.md` (Contract Holes)

## Problem
`read_time_minutes` performs a raw division with **no guard on `wpm`**:

    def read_time_minutes(text: str, wpm: int = 200) -> int:
        words = count_words(text)
        return max(1, round(words / wpm))

So the `wpm` precondition is unenforced, and two distinct failures occur
(both verified empirically):

- **`wpm == 0` → `ZeroDivisionError: division by zero`.**
  `read_time_minutes('word '*300, wpm=0)` raises.
- **`wpm < 0` → silently returns `1`.**
  `read_time_minutes('word '*300, wpm=-5)` returns `1`, because
  `round(negative)` is negative and `max(1, negative)` clamps it to `1`. A
  negative reading speed is accepted and produces a bogus "1 minute" answer
  instead of being rejected.

The docstring says "minimum 1" but never states the `wpm > 0` precondition, so
a caller cannot tell that `wpm` must be a positive integer. This is the same
unvalidated-numeric-input class as the `throttle` / `rate_limiter`
ZeroDivisionError holes (ARCH-59 / ARCH-37).

## Public contract (target)
State the precondition: **`read_time_minutes.wpm` must be a positive integer
(`wpm > 0`).** Pick ONE of the two options below and state it in the docstring
so the behavior is unambiguous:

Preferred option (document it in the docstring):
1. **Reject `wpm <= 0` up front** — raise `ValueError` with a clear message
   (e.g. `"wpm must be a positive integer"`) when `wpm <= 0`, before the
   division. Then `wpm == 0` no longer raises `ZeroDivisionError` (it raises
   `ValueError` instead) and `wpm < 0` no longer silently returns a bogus `1`.
   This is the least surprising: a caller who passes a nonsensical reading
   speed gets an explicit error, not a silently-wrong answer.
2. **Clamp `wpm` to a positive floor** — compute `wpm = max(1, wpm)` (or a
   sane floor such as `max(1, wpm)`) so the division can never be by zero and a
   negative speed cannot silently produce `1`. Then `wpm == 0` and `wpm < 0`
   both behave as `wpm == 1` (no raise, no bogus `1`). This is non-breaking but
   silently coerces invalid input, which is the weaker contract.

Regardless of option, the normal path (`wpm > 0`) must be unchanged: the
documented minimum-1 result for non-empty text and `1` for empty text.

## Behavior
- `read_time_minutes(text, wpm=0)` → does **not** raise `ZeroDivisionError`
  (option 1: raises `ValueError`; option 2: clamps to `wpm=1` and returns a
  finite value).
- `read_time_minutes(text, wpm=-5)` → does **not** silently return a bogus `1`
  (option 1: raises `ValueError`; option 2: clamps to `wpm=1` and returns a
  finite value).
- Normal path unchanged: `read_time_minutes('word '*300, wpm=200)` → `2`
  (`max(1, round(300/200))`); `read_time_minutes('', wpm=200)` → `1`.

## Guard inputs
- `read_time_minutes('word '*300, wpm=0)` → no `ZeroDivisionError` (option 1:
  `ValueError`; option 2: finite result).
- `read_time_minutes('word '*300, wpm=-5)` → no silent bogus `1` (option 1:
  `ValueError`; option 2: finite result).
- `read_time_minutes('', wpm=200)` → `1` (empty-text minimum, unchanged).

## Acceptance criteria
1. `read_time_minutes(text, wpm=0)` does **not** raise `ZeroDivisionError`
   (option 1: raises `ValueError`; option 2: returns a finite value) — pick one
   and pin it.
2. `read_time_minutes(text, wpm=-5)` does **not** silently return a bogus `1`
   (option 1: raises `ValueError`; option 2: returns a finite value) — pin the
   chosen behavior.
3. Normal path unchanged: `read_time_minutes('word '*300, wpm=200)` returns the
   documented minimum-1 result for non-empty text (`2` for 300 words at 200
   wpm), and `read_time_minutes('', wpm=200)` returns `1` for empty text
   (regression guard).

## Pinning tests to add
- `test_read_time_minutes_zero_wpm_no_zero_division`:
  `read_time_minutes('word '*300, wpm=0)` does not raise `ZeroDivisionError`
  (option 1: `pytest.raises(ValueError)`; option 2: returns a finite int).
- `test_read_time_minutes_negative_wpm_no_bogus_one`:
  `read_time_minutes('word '*300, wpm=-5)` does not silently return a bogus `1`
  (option 1: `pytest.raises(ValueError)`; option 2: returns a finite int).
- `test_read_time_minutes_normal_unchanged`:
  `read_time_minutes('word '*300, wpm=200) == 2` (non-empty minimum-1 result).
- `test_read_time_minutes_empty_text_minimum_one`:
  `read_time_minutes('', wpm=200) == 1` (empty-text regression guard).

## Docs update (same PR)
`docs/text-utils.md` — the Contract Holes section documents this hole; after
the fix, update the `read_time_minutes` entry and the Contract-holes bullet to
state the new contract (either "raises `ValueError` for `wpm <= 0`" or "clamps
`wpm` to a positive floor so the division is never by zero and a negative speed
cannot produce a bogus `1`"). Remove/adjust the Contract-holes bullet for this
hole once merged.
