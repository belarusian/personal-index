# IMPL-14: ARCH-84 fix conflicts with a validator-owned deep test (stale pin of the pre-fix stale-flag behavior)

Status: CLOSED (validator cycle 364 @ main 5793c88b; blocker cleared: reconciled tests/deep/test_domains_adversarial.py::TestRemoveListDepth::test_remove_existing to the corrected Option A contract (non-strict xfail removed, hard pin) + 4 adversarial pins + fix on main via #1786@67f23b9c; ARCH-84 VERIFIED)
Component: personal_index.domains (personal_index/domains.py) + tests/deep/test_domains_adversarial.py
Related ticket: ARCH-84 (Issue #1447)
Author: FEATURE-IMPLEMENTER (ARCH lane), cycle 313

## Blocking sentence (quoted verbatim)

ARCH-84 "Contract (what the fix must do)" mandates, verbatim:

  "In remove(), after del self._rules[domain] (and before/after
   self._save()), recompute
   self._has_whitelist = any(r.allowed for r in self._rules.values())"

and its "Acceptance Criteria" state, verbatim:

  "After add_allow("a.com") then remove("a.com"), is_allowed("unlisted.com")
   is True (allow-all restored) and list_rules() == []."

The validator-owned deep test pins the OPPOSITE (pre-fix, stale-flag) behavior.
tests/deep/test_domains_adversarial.py, class TestRemoveListDepth, function
test_remove_existing (line 220), asserts:

  m = DomainManager()
  m.add_allow("x.com")
  assert m.remove("x.com") is True
  assert m.is_allowed("x.com") is False

After remove("x.com"), "x.com" is no longer in _rules, so is_allowed("x.com")
takes the unlisted path (return not self._has_whitelist). Under the ARCH-84
fix, _has_whitelist is recomputed to False (no allow rules remain), so
is_allowed("x.com") is True. The deep test's "is False" requires the stale
_has_whitelist=True that the fix removes. The two are mutually exclusive: no
implementation can satisfy both. "x.com" after removal is exactly the
"unlisted domain" the acceptance criterion says must be allowed.

## Why the implementer cannot resolve this

- The implementer's HARD LIMITS forbid writing to tests/deep/** (validator's
  path). The stale assertion lives in
  tests/deep/test_domains_adversarial.py::TestRemoveListDepth::test_remove_existing,
  which the implementer may not edit.
- The implementer's implementation of the ARCH-84 fix is complete and correct
  per the architect's contract (remove() recompute + class/remove docstrings +
  three pinning tests in tests/test_domains.py all pass; 29 passed). The ONLY
  failing test in the full local gate is this one stale deep test, which pins
  the pre-fix stale-flag behavior.
- The implementer must not "fix" another role's file, and must not weaken the
  architect's contract to satisfy a stale pin.

## Requested resolution (VALIDATOR)

Update tests/deep/test_domains_adversarial.py::TestRemoveListDepth::
test_remove_existing to pin the corrected behavior. After
add_allow("x.com") then remove("x.com"), "x.com" is unlisted and no allow rule
remains, so the manager is not a whitelist and unlisted domains are allowed:

  m = DomainManager()
  m.add_allow("x.com")
  assert m.remove("x.com") is True
  assert m.is_allowed("x.com") is True   # unlisted + no allow rule -> allow-all

(Optionally also assert m.is_allowed("unlisted.com") is True to pin the
allow-all default explicitly.)

Once the deep test is reconciled to the corrected behavior, ARCH-84's
implementation (already on branch impl313/domains-remove-whitelist-recompute)
passes the full local gate and can be merged.

## Status of ARCH-84

Set to OPEN-PUSHBACK. The implementation is complete on the branch; it is held
pending the validator's reconciliation of the stale deep test.
