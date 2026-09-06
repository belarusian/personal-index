# TICKET-478: truncate() negative max_length produces negative slice

## File
personal_index/formatter.py

## Symptom
`truncate("hello world", max_length=-1)` returns `"hello worl"` (10 chars)
because the `max_length < 3` guard does `text[:max_length]` which is a
negative slice for negative values. The docstring explicitly warns against
negative slices ("a negative slice index would otherwise count from the end
and grow the string") but the guard itself introduces one.

## Evidence
Line 178: `return text[:max_length]` — when max_length=-1, this is
`text[:-1]` (all but last char), violating the docstring's "at most
max_length characters long" contract.

## Minimal Fix
Clamp `max_length = max(0, max_length)` at the top of the function body,
so negative values behave identically to 0 (return empty string).

## Test
Add `test_truncate_negative_max_length` asserting
`truncate("hello world", max_length=-1) == ""`.
Issue: #807
