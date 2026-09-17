# ARCH-97: cli_verify._run_filter is dead code — a duplicate filter check the full pipeline never calls

Status: VERIFIED (validator cycle 261 @ main 9bb9f60; _run_filter deleted (Option A), _verify_filter survives, full-pipeline filter rejection pinning green: tests/test_cli_verify.py 12 passed + adversarial deep test tests/deep/test_pipeline_filter_adversarial.py 12 passed incl. end-to-end CLI; docs _run_filter cleanup deferred to architect per ticket) #1564@dcf0461
Component: `personal_index/cli_verify.py`
Issue: #1488
Docs: `docs/cli_verify.md` (spec page, same PR)

## Symptom

`_run_filter` (line 209) is defined but **never called** anywhere in the
module. The full-pipeline self-test (`_check_full_pipeline`, line 262)
calls a *different* filter check, `_verify_filter` (line 291), at line 277.
The two functions duplicate the same `filter.should_include(page)` call
with different return shapes:

- `_run_filter(filter, page) -> tuple[bool, str]` (line 209) — returns
  `(False, "Content was filtered out")` on rejection, `(True, "")` on
  acceptance. **Never invoked in the production path.**
- `_verify_filter(filter, page) -> bool` (line 291) — returns
  `filter.should_include(page)`. **This is what line 277 actually calls.**

## Evidence (file:line)

- `personal_index/cli_verify.py:209` — `def _run_filter(...) -> tuple[bool, str]:`
- `personal_index/cli_verify.py:277` — `if not _verify_filter(components["filter"], page):`
  (the full pipeline's filter stage calls `_verify_filter`, not `_run_filter`)
- `personal_index/cli_verify.py:291` — `def _verify_filter(...) -> bool:`
- `grep -n '_run_filter' personal_index/cli_verify.py` returns **only** line
  209 (the `def` itself) — no call site exists in the module.
- `grep -rn '_run_filter' --include=*.py .` (excluding cli_verify.py) matches
  only `pipeline_orchestrator.py:168/202` (`_run_filter_stage`, a different
  method on a different class) — no other caller of this helper.
- `tests/test_cli_verify.py:87-107` (`test_run_filter_passes`,
  `test_run_filter_fails`) import and call `_run_filter` in isolation, pinning
  its `tuple[bool, str]` behavior — but these tests never assert that the
  production path (`_check_full_pipeline` / `verify`) uses it. They do not,
  so the dead-code status is untested.

## Why this is a hole (not a design choice)

`_run_filter`'s `tuple[bool, str]` signature matches the `_VERIFY_CHECKS`
convention (line 317) — every check in that table returns
`tuple[bool, str]`. The full-pipeline self-test is the one place a
`tuple[bool, str]` filter result would be natural (it needs the failure
message for the `✗ Full pipeline: ...` line), yet it uses the `bool`-returning
`_verify_filter` and hard-codes its own failure string
(`"Filter rejected valid content"`, line 278). The presence of a
`tuple[bool, str]` filter helper with no caller, sitting next to a
`bool`-returning twin that *is* called, is the signature of a superseded
implementation left behind — not an intentional public API (both are
private, underscore-prefixed, and not exported).

## Proposed fix (minimal, additive-or-deleting; implementer's choice)

**Option A (delete the dead helper — recommended):** remove `_run_filter`
(lines 209-222) and the two isolation tests
(`tests/test_cli_verify.py::test_run_filter_passes`,
`test_run_filter_fails`). The full pipeline already has a working filter
check (`_verify_filter`); nothing in the production path needs `_run_filter`.

**Option B (wire it in):** change line 277 to call `_run_filter` and use its
returned message, e.g.
`passed, msg = _run_filter(components["filter"], page); if not passed: return False, msg`,
then delete `_verify_filter` (line 291) and its now-redundant docstring. This
makes the full-pipeline failure message come from the shared helper instead of
a hard-coded string.

Either option removes the duplicate. Option A is smaller (pure deletion);
Option B removes the hard-coded string at line 278 as a bonus.

## Acceptance criteria

1. After the fix, `grep -n '_run_filter' personal_index/cli_verify.py`
   returns **zero** lines (Option A) OR the sole remaining filter check is
   the one `_check_full_pipeline` calls and the other is gone (Option B).
2. `verify` / `_check_full_pipeline` behavior is unchanged: a page that
   passes the filter still yields `(True, "")`; a page that fails still
   yields `(False, <non-empty reason>)`.
3. The full-pipeline failure path still produces a non-empty reason string
   (whatever the chosen option, the `✗ Full pipeline: ...` line must not
   become empty).
4. `python3 -m pytest tests/test_cli_verify.py -q` green; the full local
   gate green; CI green.

## Pinning tests to add (IMPLEMENTER writes these — architect never writes tests/**)

- **Option A:** delete `test_run_filter_passes` / `test_run_filter_fails`;
  add ONE test that pins the *production* filter path: call
  `_check_full_pipeline` with a monkeypatched `ContentFilter.should_include`
  returning `False` and assert the returned reason is non-empty and mentions
  the filter (this pins that the full pipeline's filter stage reports a
  failure, independent of which helper implements it).
- **Option B:** keep/adjust the two isolation tests to target the surviving
  helper, and add ONE test asserting `_check_full_pipeline` returns the
  helper's message (not a hard-coded string) when the filter rejects.

## Docs update (same PR)

`docs/cli_verify.md` (this PR) already lists `_run_filter` as dead in the
"Known contract holes" section and marks it in the public-surface table.
After the implementer's fix, the architect will re-audit and remove the
contract-hole bullet + the `_run_filter` row (or update it to the surviving
helper) in a follow-up docs pass.

## Self-review checklist

- [ ] Component named: `personal_index/cli_verify.py`
- [ ] Public contract stated: `_run_filter` signature + behavior + the
      `_verify_filter` twin it is dead against
- [ ] Error paths: filter-rejection reason string; the `✗ Full pipeline` line
- [ ] Guard inputs: a page failing `should_include` (the rejection path)
- [ ] Acceptance criteria: 4, verifiable by grep + pytest
- [ ] Pinning tests named (implementer-owned)
- [ ] Docs page update in the SAME PR (`docs/cli_verify.md` + README index)
- [ ] file:line evidence cited for every claim

## Docs reconciled (architect, cycle 300)

The deferred docs cleanup is closed: `docs/cli_verify.md`'s contract-hole
bullet + the `_run_filter` public-surface table row were removed and the
'Known contract holes' section restated as RESOLVED (Option A — dead
`_run_filter` deleted, cycle 261 / #1564@dcf0461); the `docs/README.md`
cli_verify index line was restated to the confirmed Option A in the same PR.
VERIFIED status unchanged.
