# IMPL-17: QA-72 deep-test conflict - validator-owned test pins pre-fix negative-slice leak behavior

- **Status:** OPEN
- **Component:** `tests/deep/test_cycle_signals_negslice_adversarial.py`
- **Kind:** deep-test conflict (validator-owned test pins pre-fix behavior)
- **Related ticket:** QA-72 (issue #1753)

## Blocking sentence

`tests/deep/test_cycle_signals_negslice_adversarial.py:104-105` (inside
`test_format_tree_negative_max_lines_is_not_empty_leak_signature`, def at line 96):

    assert len(format_tree(tree, max_depth=1, max_lines=-1).splitlines()) == full_lines - 1
    assert len(format_tree(tree, max_depth=1, max_lines=-2).splitlines()) == full_lines - 2

The test builds a 10-package flagged tree and asserts that a NEGATIVE
`max_lines` returns all-but-last lines (the Python negative-slice LEAK):
`-1 -> full_lines-1`, `-2 -> full_lines-2`.

## Why it blocks

QA-72's contract is to ADD the missing floor at the terminal slice
(`return "\n".join(lines[:max(0, max_lines)])`), so a negative `max_lines`
clamps to 0 (empty output, identical to `max_lines=0`). With that fix applied,
`format_tree(tree, max_depth=1, max_lines=-1)` returns `""` (0 lines), so the
line-104 assertion `0 == full_lines - 1` (i.e. `0 == 9`) FAILS.

This is the exact same class of conflict as IMPL-16 (QA-63) and IMPL-15
(ARCH-98): a validator-owned deep test pins the pre-fix behavior that the
ticket's contract explicitly changes. The two cannot both be true:

- QA-72 contract: negative max_lines clamps to 0 (empty).
- line-104/105 assertion: negative max_lines leaks all-but-last (full-1 / full-2).

QA-72's own "Deep test" section mischaracterizes this test as one of the
"GUARDED behaviors the module already delivers correctly (... the exact
negative-slice leak signature -1 -> full-1 / -2 -> full-2 ...)". The leak
signature is the DEFECT being fixed, not a correctly-delivered behavior; the
test pins the defect and therefore cannot survive the fix.

## Empirical confirmation (baseline, pre-fix)

`python3 -m pytest tests/deep/test_cycle_signals_negslice_adversarial.py -v`:
4 passed, 2 xfailed. `test_format_tree_negative_max_lines_is_not_empty_leak_signature`
is a REGULAR test that currently PASSES (pinning the leak). After the floor fix
it FAILS. The 2 xfail-strict pins XPASS->strict-FAIL and are flipped by the
implementer (authorized); this 3rd regular test is NOT.

## Why the implementer cannot resolve it

The conflicting test lives in `tests/deep/`, which is the VALIDATOR's path
(HARD LIMITS: implementer writes are limited to `personal_index/**` and
`tests/**` EXCEPT `tests/deep/**`). It is a REGULAR test (no
`@pytest.mark.xfail` marker), so the HARD LIMITS xfail-strict-flip exception
does NOT apply. The implementer may not edit it. Both the local gate
(`pytest tests/`) and CI (`pytest tests/ -v`, .github/workflows/ci.yml:30)
collect tests/deep, so the gate is RED after the authorized changes.

## What the architect/validator must decide

Either (a) the validator updates the line-104/105 assertions (and the test's
docstring, which currently documents the OLD leak signature) to pin the QA-72
contract (negative max_lines clamps to 0 / empty), or (b) the QA-72 contract
is re-scoped. The fix itself (`personal_index/cycle_signals.py:308` floor) is
correct and ready; only the validator-owned armor test blocks the merge.

## State left behind

- No claim, no implementation, no PR: the contract was found infeasible at the
  queue step, so QA-72 was NOT claimed (avoids a red-CI PR like IMPL-16's #1716).
- QA-72 is set to OPEN-PUSHBACK.
