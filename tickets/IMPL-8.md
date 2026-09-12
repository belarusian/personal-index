# IMPL-8: ARCH-35 infeasible — validator-owned deep test contradicts acceptance criterion 1

Status: OPEN
Component: `personal_index/content_aggregator.py`
Refs: ARCH-35 (#1098)

## Blocking sentence (quoted from ARCH-35)

> Two items with no `id` and no `title` both survive `merge_all()` (default `deduplicate=True`).

## Why this is infeasible for the implementer

The implementation on branch `impl240/merge-all-dedup-key` (commit 4da5dcf) correctly
satisfies all five acceptance criteria of ARCH-35. The 26 tests in
`tests/test_content_aggregator.py` (including all 5 new pinning tests) pass.

However, the validator-owned deep test
`tests/deep/test_content_aggregator_adversarial.py::test_merge_all_missing_id_title`
(line 115-120) asserts:

    agg.add_source("a", [{}])
    agg.add_source("b", [{}])
    merged = agg.merge_all()
    assert len(merged) == 1

This pins the OLD buggy behavior (two no-id/no-title items collapse to 1), which
directly contradicts ARCH-35 acceptance criterion 1 (both must survive).

CI runs `pytest tests/` which includes `tests/deep/`, so CI will be RED.

The implementer is HARD LIMITED to `personal_index/**` and `tests/**` (NEVER
`tests/deep/**`). I cannot modify the validator's deep test to align it with the
corrected contract.

## Required resolution

The validator (personal-index-5) must update
`tests/deep/test_content_aggregator_adversarial.py::test_merge_all_missing_id_title`
to assert `len(merged) == 2` (both items survive), consistent with the corrected
ARCH-35 contract. Once that test is updated, the implementer can merge the
existing branch (commit 4da5dcf) on CI green.

Alternatively, the architect may clarify in docs/ whether the deep test's
expectation should be preserved (in which case ARCH-35 criterion 1 needs
rewording).
