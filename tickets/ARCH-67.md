# ARCH-67 — content_annotations: `AnnotationManager.add()` is not idempotent — re-adding an `annotation_id` diverges the secondary indexes from the primary store

Status: CLAIMED (impl293, cycle 293)
Component: `personal_index/content_annotations.py` — `AnnotationManager.add` (lines 118-157), the five index appends at lines 141, 147, 152, 157
Umbrella: ARCH-2 (#983)
Issue: #1384
Docs: `docs/content_annotations.md` (Contract Holes #1)

## Problem
`add()` sets `_annotations[annotation.annotation_id] = annotation` (line 136),
which **overwrites** the primary store entry on a re-add. But the five
secondary-index appends (lines 141, 147, 152, 157) are **unconditional** —
they do not check whether the id is already indexed. A second `add()` of the
same `annotation_id` therefore leaves:

- `_annotations` at **1** entry (dict overwrite) → `count()` / `get_all()` /
  `get_stats()["total"]` report 1.
- `_by_content[cid]`, `_by_type[type]`, and (when author/tags are present)
  `_by_author[author]` / `_by_tag[tag]` each at **2** entries.

Consequences (verified against the code):
- `get_by_content_id(cid)` returns the **same annotation twice** — the
  `if i in self._annotations` filter in `get_by_content_id` (line 165) drops
  deleted ids but does **not** dedupe a duplicated index entry.
- `get_by_author` / `get_by_type` / `get_by_tag` likewise return duplicates.
- `get_stats()["by_content"]` (a `len` of `_by_content`) can disagree with
  `get_stats()["total"]` after a re-add.

The primary store and the secondary indexes are two sources of truth for the
same set of annotations, and `add()` is the only method that can make them
disagree. `delete()` is symmetric in the opposite direction (it filters every
index), so the divergence is introduced only by a duplicate `add()`.

## Public contract (target)
`add()` must be **idempotent per `annotation_id`**: after any number of
`add()` calls for the same `annotation_id`, the primary store holds exactly
one entry for that id and every secondary index holds exactly one entry for
that id (the latest annotation object wins).

Preferred option (dedupe before append):
1. In `add()`, before the five appends, if `annotation.annotation_id` is
   already in `_annotations`, first remove its stale entries from all five
   indexes (the same filter logic `delete()` uses), then set the primary
   entry and append once. Equivalently: guard each append with
   `if annotation.annotation_id not in <index-list>` so a re-add never
   appends a second copy.
2. Result: re-adding the same id is a no-op on the index sizes (each index
   list stays at 1 for that id) and the primary store stays at 1.

Alternative option (reject re-adds):
3. In `add()`, if `annotation.annotation_id` is already in `_annotations`,
   return early (no mutation). Result: the first `add()` wins; a re-add is a
   silent no-op. This is simpler but changes the "latest wins" overwrite
   semantics of the primary store.

Option 1 is preferred: it preserves the existing "latest annotation object
wins" overwrite of the primary store while making the indexes consistent.
The normal single-add path for every other id must be unchanged.

## Behavior
- `m.add(a); m.add(a)` (same `annotation_id`) → `m.count() == 1`,
  `len(m.get_by_content_id(a.content_id)) == 1`,
  `len(m.get_by_type(a.annotation_type)) == 1`,
  `len(m.get_by_tag(t)) == 1` for each tag `t`,
  `len(m.get_by_author(a.author)) == 1` when author is truthy.
- `m.add(a); m.add(a2)` (different ids, same content_id) →
  `len(m.get_by_content_id(cid)) == 2` (unchanged normal path).
- `m.add(a); m.add(a_replaced)` (same id, different object) → the primary
  store holds `a_replaced` (latest wins), and each index holds exactly one
  entry for that id.

## Guard inputs
- Re-add of the same `annotation_id` (the divergence input).
- A falsy-author annotation re-added (pins that `_by_author` is untouched on
  both adds — the guard path at line 145).
- A single-add normal path (regression guard: distinct ids still index once
  each).

## Acceptance criteria
1. `m.add(a); m.add(a)` → `m.count() == 1` AND
   `len(m.get_by_content_id(a.content_id)) == 1` AND
   `len(m.get_by_type(a.annotation_type)) == 1`.
2. `m.add(a); m.add(a)` with `a.author` truthy and `a.tags == ["t1"]` →
   `len(m.get_by_author(a.author)) == 1` AND `len(m.get_by_tag("t1")) == 1`.
3. `m.add(a); m.add(a2)` (distinct ids, same content_id) →
   `len(m.get_by_content_id(cid)) == 2` (regression guard: the normal
   multi-annotation path is unchanged).
4. `m.add(a); m.add(a_replaced)` (same id, different object) →
   `m.get(a.annotation_id) is a_replaced` (latest wins) AND each index holds
   exactly one entry for that id.
5. `m.add(a); m.add(a)` with `a.author == ""` → `m.get_by_author("") == []`
   (guard path: a falsy author is never indexed, on either add).

## Pinning tests to add
- `test_add_idempotent_no_duplicate_index_entries`: `m.add(a); m.add(a)`;
  assert `m.count() == 1`, `len(m.get_by_content_id(a.content_id)) == 1`,
  `len(m.get_by_type(a.annotation_type)) == 1`.
- `test_add_idempotent_author_tag_indexes`: `a` with `author="bob"`,
  `tags=["t1"]`; `m.add(a); m.add(a)`; assert
  `len(m.get_by_author("bob")) == 1` and `len(m.get_by_tag("t1")) == 1`.
- `test_add_distinct_ids_still_index`: `m.add(a); m.add(a2)` (same
  content_id, different ids); assert
  `len(m.get_by_content_id(cid)) == 2` (regression guard).
- `test_add_readd_latest_wins`: `m.add(a); m.add(a_replaced)` (same id);
  assert `m.get(a.annotation_id) is a_replaced` and the index lists hold one
  entry each.
- `test_add_falsy_author_never_indexed`: `a.author == ""`; `m.add(a);
  m.add(a)`; assert `m.get_by_author("") == []` (guard path).

## Docs update (same PR)
`docs/content_annotations.md` — Contract Holes #1 already documents the
re-add divergence. After the fix, update the `add()` section to state the
idempotent contract ("re-adding an `annotation_id` overwrites the primary
entry and leaves exactly one entry in each secondary index") and remove/adjust
the Contract Holes #1 callout once merged.
