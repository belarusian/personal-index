# IMPL-18: QA-73 infeasible as written - validator-owned $lte deep test pins an arithmetically incorrect expectation

- **Status:** OPEN
- **Ref:** QA-73 (issue #1756)
- **Component:** tests/deep/test_content_search_adversarial.py (test_search_filter_lte_type_mismatch_does_not_crash)

## Blocking sentence (quoted from QA-73 deep test, tests/deep/test_content_search_adversarial.py)

    # Corrected contract: no TypeError; the str item value cannot satisfy
    # $lte 3, so only the numeric item (priority=5) is kept.
    out = idx.search("one", filters={"priority": {"$lte": 3}})
    assert out["total"] == 1
    assert [r["item"].get("id") for r in out["results"]] == ["b"]

## Why infeasible

QA-73's own documented contract (ticket body, "Expected per docs"): "A non-None
item value that cannot be ordered against the filter value should be treated as
NOT satisfying the comparison (the item is dropped)." Applying that to the $lte
case (items: a priority="high" str, b priority=5 int; filter $lte 3):

- item a: str is not order-comparable to int 3 -> dropped (per contract).
- item b: 5 IS comparable; 5 > 3, so 5 does NOT satisfy $lte 3 -> dropped.

Correct result: total == 0, results == []. The test asserts total == 1 and
results == ["b"], which is arithmetically wrong for $lte 3 (5 is not <= 3). The
test comment ("only the numeric item (priority=5) is kept") reveals the author
applied the $gte logic (where 5 >= 3 keeps b) to the $lte test without flipping
the threshold expectation - a copy-paste error. The $gte sibling test
(test_search_filter_gte_type_mismatch_does_not_crash) is correct and passes.

## Why this is a pushback, not an implementer fix

The conflicting test is in tests/deep/** (the validator's path). HARD LIMITS
permit the implementer to touch tests/deep/** ONLY to remove the
@pytest.mark.xfail(strict=True) decorator (the flip) and any orphaned import
pytest - NOT to edit an assertion body. The assertion is the blocker, so the
implementer cannot make the gate green without editing the validator's file.

## Validator decision required (one of)

(a) Correct the $lte test's expected values to match the ticket contract:
    assert out["total"] == 0
    assert out["results"] == []
    (and fix the misleading comment), then re-queue QA-73; the implementer's
    fix (below) then passes both deep pins.
(b) Re-scope QA-73 if a different $lte contract is intended.

## Implementer's fix (ready, verified against the $gte pin + 4 armor pins; blocked only by the $lte assertion above)

In personal_index/content_search.py _matches_filters, replace the two
unguarded order comparisons with try/except TypeError so a non-comparable
non-None item value is dropped (treated as not satisfying), preserving the
None-skip and the exact-match / list-set branches:

    if "$gte" in value and item_value is not None:
        try:
            if item_value < value["$gte"]:
                return False
        except TypeError:
            return False
    if "$lte" in value and item_value is not None:
        try:
            if item_value > value["$lte"]:
                return False
        except TypeError:
            return False

Empirical: with this fix, the $gte pin passes (total 1, ["b"]), all 4 armor
pins pass, and the $lte pin yields total 0 / [] (the contract-correct result),
which the current $lte assertion rejects.
