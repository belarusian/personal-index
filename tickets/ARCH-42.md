# ARCH-42: annotation — add silently overwrites on an annotation_id collision AND desyncs the _by_url index

Status: IMPLEMENTED #1302@68feef9
Component: `personal_index/annotation.py`
Issue: #1119
Refs: ARCH-2 (#983 umbrella)

## Symptom

`AnnotationStore.add` (lines 77-88) is documented as "Add an annotation to the
store," but on an `annotation_id` collision the body silently does two things
the contract never states:

1. It **overwrites** the existing annotation in `_annotations` with the new
   object (a plain dict assignment, `self._annotations[annotation.annotation_id]
   = annotation`) — no merge, no error, no "already exists" signal, and the old
   object's `created_at`/`value`/`metadata`/`author` are discarded.
2. It **does not reconcile the URL index**: the new annotation's `url` is
   appended to `_by_url[new_url]`, but the old annotation's `url` still lists
   the same `annotation_id` in `_by_url[old_url]`. So after a collision where
   the new annotation has a *different* URL, `get_by_url(old_url)` returns the
   *new* annotation (whose `url` is `new_url`), and the id is now reachable
   from two URLs while the registry holds only one object. The store's
   invariant "each id maps to exactly one URL" is silently broken.

This is the same class of hole as ARCH-41 (`create_tag` silent overwrite +
`created_at` reset): a create/replace semantic that is underspecified and
silently destroys prior state.

## Public contract (the fix must preserve the happy path)

- `add(self, annotation: Annotation) -> None` — for a **new** id the behavior
  is unchanged: the annotation is registered in `_annotations` and its id is
  appended to `_by_url[annotation.url]`.
- For a **colliding** id the contract must be made explicit (pick one and
  document it in the docstring + `docs/annotation.md`):
  - **Option A (upsert with reconciliation):** overwrite the registry entry,
    preserve the new object's `created_at`, and **remove the id from the old
    URL's `_by_url` list** (if the old URL differs) before appending to the new
    URL's list, so each id maps to exactly one URL.
  - **Option B (refuse):** return a signal (or raise) when the id already
    exists, leaving both `_annotations` and `_by_url` untouched.
- Whichever option is chosen, the postcondition must hold: for every id in
  `_annotations`, the id appears in `_by_url[annotation.url]` and in **no
  other** URL's list.

## Acceptance criteria

1. Adding a brand-new annotation registers it and indexes it under its URL
   (unchanged happy path).
2. Adding an annotation whose id already exists does NOT leave the id reachable
   from two URLs: after the call, `get_by_url(old_url)` and
   `get_by_url(new_url)` together contain the id exactly once, and the object
   returned is the one actually stored in `_annotations`.
3. The chosen collision semantic (upsert-with-reconciliation vs refuse) is
   stated in the `add` docstring and in `docs/annotation.md`.
4. `get_stats()["urls_annotated"]` and `count` remain consistent with the
   registry after a collision.

## Pinning tests to add (tests/test_annotation.py)

- `test_add_new_annotation_indexes_under_url` — add one annotation, assert
  `get(id)` returns it and `get_by_url(url)` contains it.
- `test_add_id_collision_reconciles_url_index` — add `A1` with `url=old`,
  then add a *different* annotation with the same `annotation_id` but
  `url=new`; assert the id is reachable from exactly one URL (the new one),
  `get_by_url(old)` no longer returns it, and `get(id).url == new`.
- `test_add_id_collision_same_url_no_duplicate` — add `A1` with `url=u`, then
  add a colliding id with the same `url=u`; assert `get_by_url(u)` contains the
  id exactly once (no duplicate entry in the index list).

## Docs update (same PR)

`docs/annotation.md` "Contract Holes" section (already authored in this PR)
names this as the primary hole; the implementer must update the `add` entry in
the "Registry" section to state the chosen collision semantic once implemented.
