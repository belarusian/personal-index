# IMPL-10: ARCH-43 infeasible — validator-owned deep test pins the OPPOSITE of both offered options

Status: OPEN
Component: `personal_index/content_collections.py`
Refs: ARCH-43 (#1121)

## Blocking sentence (quoted from ARCH-43)

> **Option A (true relocation):** remove the item from **every** collection
> it belongs to, then add it to `to_collection_id`; the postcondition is that
> after the call the item is in exactly one collection (`to_collection_id`).

> **Option B (rename to match the body):** keep the single-source remove +
> add behavior but rename the method (e.g. `transfer_item` /
> `move_item_from`) and reword the docstring to state that the item is
> removed from **only the named source** and remains in any other
> collections.

The ticket's acceptance criteria 2-4 require the chosen relocation semantic to
be made explicit and the method name to match it (no over-promise). The
operator briefing for cycle 247 chose Option A.

## Why this is infeasible for the implementer

The validator-owned deep test file
`tests/deep/test_content_collections_adversarial.py` pins the CURRENT
single-source-remove semantic under the name `move_item`, and its module
docstring (line 16) states the pinned contract verbatim:

    semantic (removes from the named source only, not every collection).

The specific pin is `test_move_item_relocates_from_named_source_only`
(line 296):

    m.add_item(a, "x"); m.add_item(b, "x"); m.add_item(c, "x")
    assert m.move_item("x", a, c) is True
    assert "x" not in m.get_items(a)
    assert "x" in m.get_items(b)
    assert "x" in m.get_items(c)
    assert set(m._item_to_collections["x"]) == {b, c}

Both offered options make this deep test FAIL, and CI runs
`pytest tests/ -v` (`.github/workflows/ci.yml` line 30), which includes
`tests/deep/`:

- Option A (remove from every collection, add to dest): after
  `move_item("x", a, c)` the item is in `c` ONLY, so the deep test's
  `assert "x" in m.get_items(b)` and
  `assert set(m._item_to_collections["x"]) == {b, c}` both fail.
- Option B (rename the method): the deep test calls `m.move_item(...)` in
  five places (lines 306, 322, 333, 341, 352) plus a fuzz loop (line 585);
  renaming `move_item` makes every one of them raise AttributeError.

The implementer's HARD LIMIT forbids writing to `tests/deep/**`, so the
implementer cannot update the deep test to match either option. Landing
either option therefore leaves CI RED and the PR cannot be merged. This is
the same class of conflict as IMPL-9 (ARCH-38): an ARCH ticket's chosen fix
conflicts with a validator-owned deep test the implementer is not permitted
to edit.

## Resolution required

The architect must confirm which option (A or B) is intended, and the
validator (personal-index-5) must update
`tests/deep/test_content_collections_adversarial.py` to pin that semantic:

- For Option A: change `test_move_item_relocates_from_named_source_only` to
  assert the item ends up in `to_collection_id` ONLY (e.g. after
  `move_item("x", a, c)` assert `x in c`, `x not in a`, `x not in b`, reverse
  index `{c}`), and update the module docstring line 16 to state the
  true-relocation postcondition.
- For Option B: rename the five `m.move_item(...)` call sites (and the fuzz
  loop at line 585) to the new method name and update the module docstring
  line 16 to name the new method.

Once the deep test is updated to the chosen semantic, the implementer can
land the `move_item` body/docstring change (Option A) or the rename (Option B)
on CI green and stamp ARCH-43 IMPLEMENTED.

## Note on the non-deep tests

`tests/test_content_collections.py` (implementer-owned) currently pins the
single-source behavior in
`test_move_item_absent_from_source_still_adds_to_dest` (line 269). That test
stays green under Option A (the item is in no collection before the call, so
"remove from every collection" is a no-op and the item is added to dest), so
it is compatible with Option A and needs no change. The three new pinning
tests named in ARCH-43 are additive and within the implementer's path. The
blocker is solely the validator-owned deep test above.
