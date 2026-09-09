# ARCH-53 — content_search: `add_item` must remove the old tokens on a re-add

Status: OPEN
Component: `personal_index/content_search.py` — `SearchIndex.add_item`
Umbrella: ARCH-2 (#983)
Docs: `docs/content-search.md` (Contract holes)

## Problem
`SearchIndex.add_item(item)` overwrites `self._items[item_id]` but never
discards `item_id` from the `_index` / `_term_freq` entries that the PREVIOUS
value of that id contributed. Re-indexing an item under the same id with
different text leaves the stale tokens from the old text in the inverted index
and term-frequency map, while `_doc_lengths[item_id]` is overwritten to the NEW
length. Consequences:

- A search for a term that only appeared in the OLD text still returns the item
  (stale posting survives).
- `tf` / `tfidf` / `bm25` scores are computed against a doc length that no
  longer matches the stored text, so relevance is wrong.
- The only clean path is `remove_item` then `add_item`; there is no in-place
  update, and nothing documents that constraint.

## Public contract (target)
`SearchIndex.add_item(item: dict[str, Any]) -> None` — when the resolved id
(`str(item.get("id", id(item)))`) is ALREADY present in `_items`, the method
must first remove that id's stale postings (exactly what `remove_item` does:
discard the id from every `_index` / `_term_freq` entry, deleting the entry
when it becomes empty, and pop `_doc_lengths`) BEFORE indexing the new text.
For a NEW id the behavior is unchanged. After the change, re-adding an id with
different text yields the same `_index` / `_term_freq` / `_doc_lengths` state
as `remove_item(id)` + `add_item(new_item)`.

## Behavior
- New id: identical to current behavior (no removal step needed).
- Existing id: old tokens dropped, new tokens added; `_doc_lengths` reflects
  the new text; a search for an old-only term no longer returns the item.
- `remove_item` semantics unchanged.

## Guard inputs
- Re-add with a SHORTER text (old tokens strictly more than new).
- Re-add with a LONGER text (new tokens strictly more than old).
- Re-add with identical text (idempotent; state unchanged).
- Re-add where old and new share some tokens (shared tokens keep correct
  counts; old-only tokens dropped; new-only tokens added).

## Acceptance criteria
1. After `add_item(A_old)` then `add_item(A_new)` (same id, different text),
   `SearchIndex` state equals the state from a fresh index + `add_item(A_new)`.
2. A query for a term present only in `A_old` returns no result for that id.
3. A query for a term present only in `A_new` returns the id with a score
   consistent with the NEW doc length.
4. `item_count` / `term_count` are correct after a re-add (no phantom terms).
5. New-id `add_item` behavior is unchanged (existing tests still pass).

## Pinning tests to add
- `test_add_item_readd_drops_stale_tokens`: index item id `1` with text
  `"alpha beta"`, re-add id `1` with text `"gamma"`; assert a search for
  `"alpha"` returns `total == 0` and a search for `"gamma"` returns the item.
- `test_add_item_readd_matches_remove_then_add`: build two indices — one via
  re-add, one via `remove_item` + `add_item` — and assert their `_index`,
  `_term_freq`, and `_doc_lengths` are equal.
- `test_add_item_new_id_unchanged`: a single `add_item` on a fresh index
  yields the expected postings (guards the no-op path for new ids).

## Docs update (same PR)
`docs/content-search.md` — `SearchIndex.add_item` entry: state that a re-add
under an existing id first removes the old postings (equivalent to
`remove_item` + `add_item`), so stale tokens do not survive an in-place
re-index. Remove/adjust the Contract-holes bullet for this hole once merged.
