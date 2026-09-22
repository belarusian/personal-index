# IMPL-16: QA-63 deep-test conflict - validator-owned test pins pre-fix naive-lastmod-skip behavior

- **Status:** CLOSED (validator cycle 379 @ main b25096ed; deep pin already reconciled to QA-63 contract in cycle 340 - test_sitemap_adversarial.py test renamed to test_get_recent_entries_naive_lastmod_included_per_qa63_contract, asserts naive+aware both included, passes as hard pin; QA-63 CLOSED. No further edit needed.)
- **Component:** `tests/deep/test_sitemap_adversarial.py`
- **Kind:** deep-test conflict (validator-owned test pins pre-fix behavior)
- **Related ticket:** QA-63 (issue #1705)

## Blocking sentence

`tests/deep/test_sitemap_adversarial.py:360` (inside
`test_get_recent_entries_naive_lastmod_skipped_per_docstring`, def at line 345):

    assert [e.loc for e in out] == ["https://a.com/aware"]

The test builds a Sitemap with two entries - a NAIVE lastmod
(`"2099-01-01T00:00:00"`, no Z / no offset) and an AWARE lastmod
(`"2099-01-01T00:00:00Z"`) - and asserts that ONLY the aware entry is
returned, i.e. the naive entry is SKIPPED.

## Why it blocks

QA-63's contract (and its own deep test
`tests/deep/test_datetime_naive_aware_adversarial.py`) requires the OPPOSITE:
a parseable naive `lastmod` is NOT "unparseable", so it MUST be considered -
normalized to UTC (`replace(tzinfo=timezone.utc)`) and INCLUDED when within
the window, matching the reference fix `content_scoring._score_recency`.

With QA-63's fix applied, the naive 2099 entry is normalized to UTC and
included (2099 is in the future, so `(cutoff - lastmod).days` is negative and
`<= days`), so `out == [naive, aware]` and the line-360 assertion
`== ["https://a.com/aware"]` FAILS.

This is the exact same class of conflict as IMPL-15 (ARCH-98): a
validator-owned deep test pins the pre-fix behavior that the ticket's contract
explicitly changes. The two cannot both be true:

- QA-63 contract: naive lastmod INCLUDED (normalized to UTC).
- line-360 assertion: naive lastmod SKIPPED.

## Why the implementer cannot resolve it

The conflicting test lives in `tests/deep/`, which is the VALIDATOR's path
(HARD LIMITS: implementer writes are limited to `personal_index/**` and
`tests/**` EXCEPT `tests/deep/**`). It is a REGULAR test (no
`@pytest.mark.xfail` marker - `grep -c xfail` on the file returns 0), so the
HARD LIMITS xfail-strict-flip exception does NOT apply. The implementer may
not edit it.

## What the architect/validator must decide

Either (a) the validator updates the line-360 assertion (and the test's
docstring, which currently documents the OLD skip behavior) to pin the
QA-63 contract (naive lastmod included as UTC), or (b) the QA-63 contract is
re-scoped so that a naive lastmod is still skipped, in which case the fix in
`personal_index/sitemap.py` must not normalize naive -> UTC. The two
validator-owned deep files (`test_sitemap_adversarial.py` and
`test_datetime_naive_aware_adversarial.py`) currently encode contradictory
contracts for the same code path and must be reconciled by the validator.

## State left behind

- Branch `impl353/qa63-naive-aware-datetime` (claim commit 3e69a2d4 + fix
  commit e40b32ff) is preserved on origin; PR #1716 was CLOSED (red CI) and
  is NOT merged.
- QA-63 is set to OPEN-PUSHBACK.
