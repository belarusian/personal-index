# IMPL-19: QA-74 infeasible as written - validator-owned deep test pins the pre-fix empty-key data-loss behavior

- **Status:** CLOSED (validator cycle 360 @ main d3a334d5; blocker cleared: reconciled tests/deep/test_content_dedup_adversarial.py::TestDedupAll::test_empty_url_content_not_grouped to the post-fix contract (non-strict xfail removed, hard pin) + fix on main via #1777@ab28f409; QA-74 VERIFIED)
- **Ref:** QA-74 (issue #1764)
- **Component:** tests/deep/test_content_dedup_adversarial.py (TestDedupAll::test_empty_url_content_not_grouped)

## Blocking sentence (quoted from the conflicting validator deep test, tests/deep/test_content_dedup_adversarial.py)

    r = ContentDeduplicator().dedup_all(
        [{"url": "", "content": ""}, {"url": "", "content": ""}])
    assert r.total_items == 2
    assert r.removed_count == 0
    assert r.unique_items == 2
    assert r.duplicate_groups == []

Its comment states the defect as if it were the contract: "the intermediate
list fed to the next stage collapses to the first survivor, but the reported
field does not."

## Why infeasible

QA-74's documented contract (ticket body, "Expected per docs", option b, which
the cycle-366 briefing directs): "the dropped item is counted in removed_count
so unique_items reflects the true survivor count." The dedup_all URL rebuild
collapses all-but-first empty-URL items to one survivor but never counts the
drop, so unique_items overstates the survivor count (silent data loss).

Applying the fix to the conflicting test's input (two items, both empty URL and
both empty content):

- URL rebuild: item[1] has an empty normalize_url key already seen -> dropped.
  dedup_by_url SKIPS empty URLs (never groups them), so this drop is NOT in
  url_result.removed_count. Counting it (the fix) makes url_rebuild_dropped = 1.
- Hash rebuild: only item[0] remains -> no further drop.

Correct result per the ticket: removed_count == 1, unique_items == 1. The test
asserts removed_count == 0 and unique_items == 2 - i.e. it pins the exact
silent-data-loss behavior QA-74 exists to eliminate. The fix and the assertion
cannot both hold.

## Why this is a pushback, not an implementer fix

The conflicting test is in tests/deep/** (the validator's path). HARD LIMITS
permit the implementer to touch tests/deep/** ONLY to remove the
@pytest.mark.xfail(strict=True) decorator (the flip) and any orphaned import
pytest - NOT to edit a regular (non-xfail) assertion body. This test is a
regular test with no xfail marker, so the flip exception does not apply. The
assertion is the blocker, so the implementer cannot make the local gate
(pytest tests/) or CI green without editing the validator's file. This is the
same class as IMPL-17 (QA-72) and IMPL-18 (QA-73): a validator-owned deep test
pins the pre-fix behavior the contract changes.

## Validator decision required (one of)

(a) Update the conflicting test to pin the corrected contract, then re-queue
    QA-74. With the fix applied, the corrected assertions are:
    assert r.total_items == 2
    assert r.removed_count == 1
    assert r.unique_items == 1
    assert r.duplicate_groups == []
    (and fix the misleading comment, which currently states the defect as the
    contract). The implementer's fix (below) then passes both QA-74 xfail pins
    and this armor test.
(b) Re-scope QA-74 if a different empty-key contract is intended (e.g. option
    (a) of the ticket - do not collapse distinct-content empty-URL items - but
    note that option (a) ALSO changes this test's expected unique_items, since
    the hash rebuild still collapses the two empty-content items to one).

## Implementer's fix (ready, verified against the QA-74 xfail pins + 11 armor pins; blocked only by the assertion above)

In personal_index/content_dedup.py dedup_all, count the empty-key drops made by
the two rebuild loops (which dedup_by_url / dedup_by_hash skip and therefore
never report) and add them to total_removed, so unique_items = len(items) -
total_removed reflects the true survivor count:

    seen_urls = set()
    unique_items = []
    url_rebuild_dropped = 0
    for item in items:
        normalized = normalize_url(item.get("url", ""))
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique_items.append(item)
        elif not normalized:
            url_rebuild_dropped += 1
    ...
    seen_hashes = set()
    hash_unique = []
    hash_rebuild_dropped = 0
    for item in unique_items:
        h = content_hash(item.get("content", ""))
        if h not in seen_hashes:
            seen_hashes.add(h)
            hash_unique.append(item)
        elif not h:
            hash_rebuild_dropped += 1
    ...
    total_removed = (
        url_result.removed_count
        + hash_result.removed_count
        + sim_result.removed_count
        + url_rebuild_dropped
        + hash_rebuild_dropped
    )

Only the EMPTY-key drops are added (non-empty duplicate URLs dropped by the
rebuild are already counted by url_result.removed_count, so counting them again
would double-count). Empirical: with this fix, both QA-74 xfail pins pass
(repro empty-URL distinct-content -> unique_items 1; empty-content distinct-URL
-> unique_items 1), all 11 other deep pins in
test_content_dedup_dedup_all_adversarial.py pass, and the implementer-owned unit
test test_dedup_all_pins_returned_fields_and_two_stage_pipeline
(tests/test_content_dedup.py) updates cleanly (removed_count 2 -> 3,
unique_items 4 -> 3 for its two empty-URL items). The ONLY remaining failure is
the validator-owned test_empty_url_content_not_grouped assertion quoted above.
