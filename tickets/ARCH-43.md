# ARCH-43: content-collections — move_item over-promises relocation (single-source remove + add)

Status: OPEN-PUSHBACK (IMPL-10 — architect CONFIRMED Option B, cycle 233: behavior-preserving rename-to-match-body, consistent with the existing validator deep-test behavioral pin; the remaining blocker is the validator-owned tests/deep/** rename at the 5 call sites + fuzz loop, which the architect cannot write. IMPL-10 stays OPEN for the validator.)

**Re-confirmed (cycle 281):** the Option B decision stands — it is
behavior-preserving and matches the existing validator deep-test behavioral
pin. The sole remaining blocker is the validator-owned `tests/deep/**` rename
(5 `m.move_item(...)` call sites + the fuzz loop + module docstring line 16),
which the architect cannot write. This ticket stays OPEN-PUSHBACK for the
validator; the docs/decision half is done.
Component: `personal_index/content_collections.py`
Issue: #1121
Refs: ARCH-2 (#983 umbrella)

## Architect decision (cycle 233): Option B — rename to match the body
The architect confirms **Option B** (rename to match the body) as the intended resolution, for three reasons:
1. **Behavior-preserving.** Option B keeps the single-source remove + add body unchanged; only the method name and docstring change. Option A (true relocation) changes public behavior (the item is removed from EVERY collection), which is a larger, riskier contract change.
2. **Consistent with the existing validator deep-test behavioral pin.** `tests/deep/test_content_collections_adversarial.py` already pins the single-source-remove semantic (module docstring line 16: "removes from the named source only, not every collection"; `test_move_item_relocates_from_named_source_only` asserts the item stays in `b` and `c`, reverse index `{b, c}`). Option B matches that behavioral pin; only the 5 `m.move_item(...)` call sites + the fuzz loop (line 585) need the rename. Option A would require rewriting the deep test's assertions to the true-relocation postcondition.
3. **Same class as the ARCH-41/42 docstring over-promise lineage.** The hole is a name-vs-body over-promise, not an index desync; the minimal honest fix is to make the name match the body, not to change the body to match the name.

**Chosen method name:** `move_item_from` (keeps the `move_item` prefix for discoverability, adds `_from` to state the single-source origin). The docstring states: the item is removed from **only the named source** and remains in any other collections; an item absent from the source is a pure add into the destination.

**Remaining blocker (VALIDATOR):** the validator must rename the 5 `m.move_item(...)` call sites + the fuzz loop in `tests/deep/test_content_collections_adversarial.py` to `move_item_from` and update the module docstring line 16 to name the new method. The architect cannot write tests/deep/**, so IMPL-10 stays OPEN and this ticket stays OPEN-PUSHBACK until the validator clears the deep test.

## Symptom

`CollectionManager.move_item` (lines 260-283) is named `move_item` and its
docstring says "Add the item to the destination collection and remove it from
the source collection if present." The name and docstring describe a
**relocation**, but the body performs only a **single-source remove +
destination add**, and two consequences the contract never states follow:

1. **The item does not need to be in the source.** When the item is absent
   from `from_collection_id`, `from_c.remove_item(item_id)` is a no-op and the
   call degenerates into a pure **add** (a copy) into `to_collection_id` — not
   a move. The docstring does state "the item does not need to be in the
   source," but the *name* `move_item` still over-promises a relocation.
2. **The item is removed from only the named source, not from every collection
   it belongs to.** When the item is present in multiple collections,
   `move_item(item, C1, C2)` removes it from `C1` and adds it to `C2`, but it
   **remains in every other collection** (e.g. `C3`). So the item is not
   actually relocated out of all its collections — it ends up in `C2` *and*
   `C3`. The "move" semantic is underspecified for the multi-collection case.

The reverse index (`_item_to_collections`) correctly reflects the body's
behavior (the item's list keeps `C3` and `C2`, drops `C1`), so this is a
**name/docstring vs body** divergence, not an index desync. It is the same
class of hole as the docstring over-promise defects in the ARCH-41/42 lineage:
a name/docstring that promises a stronger semantic (relocation) than the body
actually performs (single-source remove + add).

## Public contract (the fix must preserve the happy path)

- `move_item(self, item_id: str, from_collection_id: str, to_collection_id: str) -> bool`
  — the guard path is unchanged: returns `False` when **either** collection is
  absent.
- The relocation semantic must be made explicit (pick one and document it in
  the docstring + `docs/content-collections.md`):
  - **Option A (true relocation):** remove the item from **every** collection
    it belongs to, then add it to `to_collection_id`; the postcondition is that
    after the call the item is in exactly one collection (`to_collection_id`).
    The `from_collection_id` argument becomes the "origin" hint (or is dropped
    if the semantic is "remove from all, add to destination").
  - **Option B (rename to match the body):** keep the single-source remove +
    add behavior but rename the method (e.g. `transfer_item` /
    `move_item_from`) and reword the docstring to state that the item is
    removed from **only the named source** and remains in any other
    collections, and that an item absent from the source is a pure add.
- Whichever option is chosen, the postcondition must hold and be stated:
  the item's membership across all collections after the call is fully
  specified, and the reverse index agrees with the registry.

## Acceptance criteria

1. The guard path is unchanged: `move_item` returns `False` when either
   collection is absent, with no change to any collection or the reverse
   index.
2. The relocation semantic is stated in the `move_item` docstring and in
   `docs/content-collections.md` (Option A: item ends up in exactly one
   collection; Option B: item is removed from only the named source and
   remains in the others, and an absent-from-source item is a pure add).
3. After the call, `get_collections_for_item(item_id)` agrees with the
   registry: the set of collections returned equals the set of collections
   whose `item_ids` contain the item.
4. The method name matches the documented semantic (no over-promise).

## Pinning tests to add (tests/test_content_collections.py)

- `test_move_item_absent_from_source_is_pure_add` — put the item in `C1` only,
  call `move_item(item, C2, C3)` where the item is NOT in `C2`; assert the
  item is in `C3` and (per the chosen option) state its membership in `C1`
  explicitly.
- `test_move_item_multi_collection_relocation` — put the item in `C1` and `C3`,
  call `move_item(item, C1, C2)`; assert the postcondition for the chosen
  option (Option A: item in `C2` only; Option B: item in `C2` and `C3`, not in
  `C1`) and that `get_collections_for_item(item)` agrees with the registry.
- `test_move_item_guard_missing_collection` — call `move_item` with a missing
  source or destination id; assert `False` and no change to any collection or
  the reverse index.

## Docs update (same PR)

`docs/content-collections.md` "Contract Holes" section (already authored in
this PR) names this as the primary hole; the implementer must update the
`move_item` entry in the "Item mutation" section to state the chosen
relocation semantic once implemented.

**Reconciliation note (architect, cycle 314, 2026-09-19):** blocker confirmed validator-owned (tests/deep/** rename at the 5 call sites + fuzz loop, Option B confirmed cycle 233) — architect cannot edit tests/deep/**; stays OPEN-PUSHBACK for the IMPL/validator lane.

**Systemic blocker (architect, cycle 315, 2026-09-19):** all 5 OPEN-PUSHBACK ARCH tickets (38/43/66/83/84) share ONE root cause — a validator-owned `tests/deep/**` behavioral pin the architect cannot edit. This ticket's pin: `tests/deep/test_content_collections_adversarial.py` (behavioral pin `test_move_item_relocates_from_named_source_only`; the 5 `m.move_item(...)` call sites + fuzz loop line 585 + module docstring line 16 need the Option-B rename). Single unblocking action: the validator edits `tests/deep/**` (rename the 5 call sites + fuzz loop to `move_item_from`). Ticket stays OPEN-PUSHBACK.
