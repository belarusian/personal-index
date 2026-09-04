# TICKET-377 — truncate() negative-slice bug for max_length < 3

- Status: RESOLVED (merged to main 35d6a8d, gh #592 closed)
- Class: (a) behavioral
- File: personal_index/formatter.py
- Function: truncate(text, max_length=100)

## Symptom
When `max_length < 3`, `truncate()` returns a string **longer** than the input,
violating the docstring promise "Truncate text to max_length".

## Evidence
Line 171: `return text[: max_length - 3] + "..."`
For `max_length = 2`, `max_length - 3 == -1`, so `text[:-1]` drops only the last
character and then appends `"..."`:
  >>> truncate("hello world", max_length=2)
  'hello worl...'   # len 13, not <= 2
  >>> truncate("hello world", max_length=1)
  'hello wor...'    # len 12
  >>> truncate("hello world", max_length=0)
  'hello wo...'     # len 11
The negative slice index counts from the end, so the result grows instead of
shrinking. `max_length == 3` is already correct (`text[:0] + "..."` == "...").

## Minimal additive fix
Guard the no-room-for-ellipsis case before the slice:
  if max_length < 3:
      return text[:max_length]
This preserves existing behavior for `max_length >= 3` and guarantees
`len(result) <= max_length` for the sub-3 range.

## Test (fails pre-fix, passes post-fix)
tests/test_formatter.py :: TestTruncate :: test_truncation_small_max_length
  assert truncate("hello world", max_length=2) == "he"
  assert len(truncate("hello world", max_length=2)) <= 2

## Issue: #592
