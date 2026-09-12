# ARCH-35: content_aggregator — `merge_all` dedup key collapses items with both `id` and `title` falsy, silently dropping them on the default path

Status: OPEN-PUSHBACK (IMPL-8: validator deep test test_merge_all_missing_id_title pins old collapse behavior, contradicts criterion 1; cannot edit tests/deep/**)
Component: `personal_index/content_aggregator.py`
Issue: #1098
Refs: ARCH-2 (#983 umbrella)

## Symptom

`ContentAggregator.merge_all(deduplicate: bool = True)` deduplicates with the
key `str(item.get("id") or item.get("title"))`. The `or` chain falls through
to `title` whenever `id` is **falsy** (absent, `None`, `""`, `0`, `False`),
and `str()` is applied to the result. Two distinct failure modes:

- **Both `id` and `title` absent/falsy → one shared key.** An item with no
  `id` and no `title` yields `str(None or None)` = `"None"`; an item with
  `id=""` and `title=""` yields `str("" or "")` = `""`. Every such item maps
  to the *same* key, so with the **default** `deduplicate=True` only the
  **first** survives and the rest are silently dropped. This is data loss on
  the default code path with no warning, no error, and no signal to the
  caller.
- **`str()` collapses distinct id types.** `id=1` (int) and `id="1"` (str)
  both key to `"1"` and are treated as duplicates; a falsy `id=0` falls back
  to `title` even though `0` is a legitimate id.

The docstring says "keyed on the item's `id` (falling back to `title`)" but
never states that items lacking both are collapsed, so the over-promise is
hidden. This is the single most important hole in the module: it is the only
behavior that silently **loses data** on the default call.

## Public contract (target)

`merge_all(deduplicate=True)` must deduplicate on a key that is **unique per
distinct item** and must not collapse distinct items that merely lack both
`id` and `title`. A defensible contract:

- Dedup key = the item's `id` when `id` is present and non-`None` (do **not**
  use a truthiness `or` that treats `0`/`""` as absent); fall back to `title`
  only when `id` is `None`/absent.
- Items with **both** `id` and `title` absent must each be kept (they are
  distinct items), or the method must raise / document that such items are
  indistinguishable and dropped.
- Do not `str()`-collapse distinct id types (int `1` and str `"1"` are
  different ids).

## Acceptance criteria

1. Two items with no `id` and no `title` both survive `merge_all()` (default
   `deduplicate=True`).
2. `id=1` (int) and `id="1"` (str) are treated as **distinct** and both
   survive.
3. A falsy-but-present `id=0` is honored as an id (does not fall back to
   title) and `id=0` + `id="0"` are distinct.
4. True duplicates (same non-falsy `id`) still collapse to the first
   occurrence.
5. `merge_all(deduplicate=False)` still returns every item in source
   insertion order.

## Pinning tests to add (implementer)

- `test_merge_all_keeps_items_with_no_id_and_no_title`: two sources each
  contributing an item with neither `id` nor `title`; assert both are present
  in the default `merge_all()` result (pins the data-loss guard path).
- `test_merge_all_int_vs_str_id_distinct`: items `{"id": 1}` and `{"id": "1"}`
  both survive the default merge.
- `test_merge_all_falsy_id_zero_honored`: `{"id": 0, "title": "a"}` and
  `{"id": 0, "title": "b"}` are distinct (both survive) — pins that `0` is
  not treated as absent.
- `test_merge_all_true_duplicates_collapse`: two items with the same
  non-falsy `id` collapse to the first occurrence (normal case).
- `test_merge_all_no_dedup_returns_all`: `deduplicate=False` returns every
  item in insertion order.

## Docs

`docs/content-aggregator.md` (authored this cycle) documents the current
behavior and lists this as the primary contract hole. Update the
`merge_all` entry and the "Contract Holes" section in the **same PR** that
implements the fix, so the page reflects the corrected key semantics.
