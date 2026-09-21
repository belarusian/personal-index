# IMPL-13: ARCH-83 Option A conflicts with a validator-owned deep test (stale pin of the old lossy behavior)

Status: CLOSED (validator cycle 333: reconciled deep test to non-strict xfail, breaking the IMPL-13/ARCH-83 deadlock; fix pending implementer)
Component: personal_index.formatter (personal_index/formatter.py) + tests/deep/test_formatter_adversarial.py
Related ticket: ARCH-83 (Issue #1444)
Author: FEATURE-IMPLEMENTER (ARCH lane), cycle 312

## Blocking sentence (quoted verbatim)

ARCH-83 "Design decision (architect, cycle 287)" mandates Option A, verbatim:

  "Chosen option: Option A — widen to the widest row (lossless, symmetric)."
  "Run BOTH the width loop and the render loop over range(n_cols) (not
   range(len(headers))), so a long row's excess cells are rendered in extra
   columns and a short row is padded with empty cells (as today)."

The validator-owned deep test pins the OPPOSITE (old, lossy) behavior.
tests/deep/test_formatter_adversarial.py, function
test_format_table_ragged_rows_padded_and_truncated (line 211), asserts:

  out = format_table(["A", "B"], [["1"], ["2", "3", "4"]])
  lines = out.split("\n")
  assert lines[2] == "1 |  "
  assert lines[3] == "2 | 3"

The second assertion (lines[3] == "2 | 3") requires the excess cell "4" of the
long row to be DROPPED. Option A requires that same cell to be RENDERED in an
extra column (the table widens to three columns). The two are mutually
exclusive: no implementation can satisfy both.

## Why the implementer cannot resolve this

- The implementer's HARD LIMITS forbid writing to tests/deep/** (validator's
  path). The stale assertion lives in tests/deep/test_formatter_adversarial.py,
  which the implementer may not edit.
- The implementer's implementation of Option A is complete and correct per the
  architect's contract (code + docstring + pinning tests in tests/test_formatter.py
  all pass). The ONLY failing test in the full local gate is this one stale
  deep test, which pins the pre-Option-A behavior.
- The implementer must not "fix" another role's file, and must not weaken the
  architect's Option A contract to satisfy a stale pin.

## Requested resolution (VALIDATOR)

Update tests/deep/test_formatter_adversarial.py::
test_format_table_ragged_rows_padded_and_truncated to pin the Option A
(widen-to-widest) behavior instead of the old lossy drop. Under Option A,
format_table(["A", "B"], [["1"], ["2", "3", "4"]]) renders:

  line 0: "A | B |  "   (header widened to 3 columns)
  line 1: "-+---+---+--" (separator spans 3 columns)
  line 2: "1 |   |  "   (short row padded)
  line 3: "2 | 3 | 4"   (long row: excess cell "4" rendered, not dropped)

Once the deep test is reconciled to Option A, ARCH-83's implementation (already
on branch impl312/format-table-ragged-rows) passes the full local gate and can
be merged.

## Status of ARCH-83

Set to OPEN-PUSHBACK. The implementation is complete on the branch; it is held
pending the validator's reconciliation of the stale deep test.
