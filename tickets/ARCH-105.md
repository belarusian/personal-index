# ARCH-105 — app.py `shutdown()` is a log-only no-op: dead `if self._interest_store:` guard + false "no save method" docstring claim

- **Status:** VERIFIED (validator cycle 270 @ main 1fafeb3; shutdown() docstring corrected (no false "no save method" claim; states InterestStore self-persists on mutation); pinning tests green tests/test_app.py 49 passed; NOTE docs gap (architect-owned, reconcile at close): docs/app.md "Known contract holes" still describes shutdown() in present tense with the dead `if self._interest_store: pass` guard + false "no save method" docstring claim, but the live code has the guard removed and the docstring corrected; [was IMPLEMENTED #1582@faafbba])
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/app.py (DEAD module — 0 importers; see docs/app.md) + personal_index/interests.py (the live InterestStore it references)
- **Issue:** #1511

## Symptom

`PersonalIndexApp.shutdown()` is documented as "Clean up application
resources" but performs no cleanup. Its body is:

    if self._interest_store:
        # InterestStore doesn't have a save method, just pass
        pass
    logger.info("PersonalIndexApp shutdown complete")

Two distinct defects in one method:

1. **Dead guard.** The `if self._interest_store:` branch is a bare `pass` —
   the guard tests a field whose branch does nothing. Whether the interest
   store was ever accessed or not, the method's observable effect is
   identical (one log line). The guard is dead code.
2. **False docstring claim.** The docstring (app.py:342) justifies the no-op
   with "No persistence, no component teardown (InterestStore has no save
   method)". That claim is FALSE: `InterestStore` DOES have a save method —
   `_save` at interests.py:44 — and it is invoked on every mutation
   (`add` at interests.py:58, `remove` at interests.py:63). The rationale
   for the no-op is therefore wrong, and the docstring over-promises a
   design constraint that does not hold.

Because app.py is a DEAD module (never imported), this is the
dead-module + divergent-contract class (ARCH-100/102 pattern): the module
ships a public `shutdown()` whose contract (teardown) it does not fulfill,
and whose docstring states a false invariant about the live `InterestStore`
it references.

## Evidence (file:line)

- personal_index/app.py:333 — `def shutdown(self):`.
- personal_index/app.py:336-337 — docstring "Guard path: when
  ``self._interest_store`` is falsy (never accessed), the (currently empty)
  cleanup block is skipped."
- personal_index/app.py:342 — docstring "No persistence, no component
  teardown (InterestStore has no save method)." — FALSE claim.
- personal_index/app.py:344-345 — `if self._interest_store:` /
  `# InterestStore doesn't have a save method, just pass` / `pass` — dead
  guard, no teardown.
- personal_index/app.py:347 — `logger.info("PersonalIndexApp shutdown
  complete")` — the method's only observable effect.
- personal_index/interests.py:44 — `def _save(self) -> None:` — the save
  method the docstring claims does not exist.
- personal_index/interests.py:58 — `add` calls `self._save()`.
- personal_index/interests.py:63 — `remove` calls `self._save()`.
- DEAD-MODULE witness: `grep -rn 'personal_index.app\|from .app\|import app\b\|PersonalIndexApp' personal_index/ --include=*.py`
  returns only `pipeline.py:110` (a docstring mention), no import — app.py
  is never wired.

## Proposed fix (implementer)

Make the docstring TRUE and the guard meaningful, or remove the dead guard.
Minimal additive options (pick one; do NOT change live behavior of any
imported module):

- **Option A (doc-only, recommended):** reword the `shutdown()` docstring to
  state the EXACT contract — "Performs no component teardown and no
  persistence; logs a shutdown-complete message. `InterestStore` persists
  itself on every mutation (interests.py:44 `_save`, called from `add`/
  `remove`), so there is nothing to flush at shutdown." — and delete the
  dead `if self._interest_store: pass` block (or keep it and document it as
  intentionally empty). This is a doc-only + dead-code-removal change to a
  dead module; no live path is affected.
- **Option B (behavioral):** if teardown is genuinely wanted, implement it
  (e.g. flush/close the components that own resources). This is a larger
  change and only warranted if a live path is later added that constructs
  `PersonalIndexApp`.

## Acceptance criteria

1. The `shutdown()` docstring no longer claims "InterestStore has no save
   method"; it states the actual contract (no teardown, log-only) and the
   true reason (InterestStore self-persists on mutation).
2. The dead `if self._interest_store: pass` guard is either removed or
   explicitly documented as intentionally empty.
3. No live module's behavior changes (app.py has 0 importers; the change is
   confined to app.py).
4. docs/app.md "Known contract holes" entry for ARCH-105 is updated to
   reflect the resolution (shipped in the SAME PR as the code/doc fix).

## Pinning tests to add (implementer)

- One behavior test that pins the CORRECTED contract against the returned
  object / actual effect: construct a `PersonalIndexApp` in a temp
  `data_dir`, call `add_interest(...)` (which persists via
  `InterestStore._save`), then call `shutdown()` and assert the observable
  effect is exactly the log line (no new file, no teardown side effect) —
  i.e. the test pins that `shutdown()` is log-only AND that the interest
  store was already persisted by `add` (witnessing the corrected "self-
  persists on mutation" claim). Include the GUARD-PATH input: also assert
  the same log-only effect when `shutdown()` is called on a fresh app that
  never accessed `interest_store` (the falsy-guard path), so one test pins
  both the accessed and never-accessed branches.
- WITNESS-ROLE note: the architect does not write tests/**; the implementer
  adds this test. If a validator deep test already pins the current
  log-only behavior, that test is the witness that the corrected docstring
  matches reality and the fix is doc-only.

## Self-review checklist (architect)

- [x] Component named (app.py, dead module) + live twin (interests.py).
- [x] Public contract stated (shutdown signature + behavior + guard path).
- [x] Error paths / guard inputs named (falsy `_interest_store` branch).
- [x] file:line evidence for every claim (app.py:333/342/344-347;
      interests.py:44/58/63; dead-module grep witness).
- [x] Acceptance criteria + pinning tests specified.
- [x] docs/app.md update ships in the SAME PR.
- [x] No personal_index/** or tests/** written by architect (design-only).
