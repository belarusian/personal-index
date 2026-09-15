# ARCH-84: DomainManager.remove() leaves _has_whitelist stale — removing the last allow rule silently flips unlisted domains to deny-all

Status: OPEN
Component: personal_index.domains (personal_index/domains.py)
Issue: #1447

## Symptom

`DomainManager` tracks whether it is a **whitelist** in the private flag
`_has_whitelist`. The flag is set to `True` by `add_allow()` (line 108) and
recomputed in `_load()` (line 88-89, `any(r.allowed for r in _rules.values())`).
But `remove()` (line 183-192) deletes the rule and calls `_save()` **without
recomputing `_has_whitelist`**.

Consequence: after `add_allow("a.com")` then `remove("a.com")`, no allow rule
remains, yet `_has_whitelist` is still `True`. `is_allowed()` (line 140-147)
for any **unlisted** domain returns `not self._has_whitelist` -> `False`. So the
manager silently becomes a **deny-all whitelist** even though the rule set is
empty. The intended allow-all default (`is_allowed("anything.com") is True`
when no rules exist) is lost.

The existing tests only assert the *removed domain's own* status after
`remove()` (`test_remove_existing` asserts `is_allowed("x.com") is False`,
`test_remove_rule` asserts `is_blocked("spam.com") is False`) — never an
**unlisted** domain — so the stale flag is unpinned.

## Evidence

- `personal_index/domains.py:108` — `add_allow` sets `self._has_whitelist = True`.
- `personal_index/domains.py:88-89` — `_load` recomputes
  `self._has_whitelist = any(r.allowed for r in _rules.values())`.
- `personal_index/domains.py:183-192` — `remove` does `del self._rules[domain]`
  + `self._save()` + `return True`; **no `_has_whitelist` recompute**.
- `personal_index/domains.py:140-147` — `is_allowed` unlisted path returns
  `not self._has_whitelist`.
- Verified against the code (repro):
  - `m = DomainManager(); m.add_allow("a.com")`
  - `m.is_allowed("unlisted.com")` -> `False` (whitelist active)
  - `m.remove("a.com")`
  - `m.is_allowed("unlisted.com")` -> `False` (BUG: should be `True`, no rules)
- `tests/test_domains.py:70-79` (`test_remove_rule`, `test_remove_nonexistent`)
  and `tests/deep/test_domains_adversarial.py:220-228` (`test_remove_existing`,
  `test_remove_missing`) — none assert an unlisted domain after `remove()`.

## Failing input / observed vs expected

- Input: `add_allow("a.com")` -> `remove("a.com")` -> `is_allowed("unlisted.com")`.
- Observed: `False` (stale `_has_whitelist` keeps the whitelist active).
- Expected: `True` — with no rules present the manager is not a whitelist, so
  unlisted domains are allowed (the documented allow-all default).
- Contrast (NOT a hole): `add_block("b.com")` -> `remove("b.com")` ->
  `is_allowed("unlisted.com")` is already `True`, because `add_block` never set
  the flag and a block-only set is not a whitelist. The bug is specific to
  removing an **allow** rule that was the last (or only) allow rule.

## Contract (what the fix must do)

Make `remove()` keep `_has_whitelist` consistent with the surviving rule set,
and document the invariant. The minimal, correct change:

1. In `remove()`, after `del self._rules[domain]` (and before/after
   `self._save()`), recompute
   `self._has_whitelist = any(r.allowed for r in self._rules.values())` —
   the same expression `_load()` uses, so the flag is derived from the rule
   set in exactly one place's semantics.
2. Update the `remove()` docstring to state: "Removes the rule for `domain`
   and re-derives the whitelist flag from the surviving rules; returns True if
   a rule was removed, False if not found."
3. State the invariant in the class docstring: "`_has_whitelist` is always
   `any(r.allowed for r in _rules.values())` — it is recomputed on load and on
   every rule removal, and set on every allow."

Do NOT change `add_allow`/`add_block`/`is_allowed` semantics; the fix is
localized to `remove()` plus docstrings.

## Acceptance Criteria

- After `add_allow("a.com")` then `remove("a.com")`, `is_allowed("unlisted.com")`
  is `True` (allow-all restored) and `list_rules() == []`.
- After `add_allow("a.com")` + `add_allow("b.com")` then `remove("a.com")`,
  `is_allowed("unlisted.com")` is still `False` (a whitelist remains because
  `b.com` is still allowed) and `is_allowed("b.com")` is `True`.
- After `add_block("b.com")` then `remove("b.com")`, `is_allowed("unlisted.com")`
  is `True` (unchanged, block-only was never a whitelist).
- `remove()` still returns `True` when a rule existed and `False` when not, and
  still persists to `rules_file` on removal.
- The `remove()` and class docstrings state the whitelist recompute invariant.

## Pinning tests to add

Add to `tests/test_domains.py` (unit) — tests that pin the corrected claim
against the returned object, including the guard/contrast path:

    def test_remove_last_allow_restores_allow_all(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("a.com")
        assert dm.is_allowed("unlisted.com") is False   # whitelist active
        assert dm.remove("a.com") is True
        assert dm.list_rules() == []
        assert dm.is_allowed("unlisted.com") is True    # allow-all restored (the fix)

    def test_remove_one_of_many_keeps_whitelist(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("a.com")
        dm.add_allow("b.com")
        assert dm.remove("a.com") is True
        assert dm.is_allowed("unlisted.com") is False   # whitelist still active
        assert dm.is_allowed("b.com") is True

    def test_remove_block_keeps_allow_all(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_block("b.com")
        assert dm.remove("b.com") is True
        assert dm.is_allowed("unlisted.com") is True    # block-only was never a whitelist

The first test pins the main behavior (stale-flag fix) AND the guard path
(`list_rules() == []` after removal). The second pins the "whitelist survives
when another allow remains" contrast. The third pins the block-only contrast so
the fix does not over-correct.

## Docs

`docs/domains.md` (this cycle) already lists this as the contract hole and
documents the `_has_whitelist` invariant; the implementer's fix PR must keep
that page accurate (the "Contract holes" bullet for ARCH-84 becomes resolved
and the invariant line stays true).
