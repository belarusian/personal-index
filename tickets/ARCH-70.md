# ARCH-70 — content_analytics: `get_items_by_tag` substring-matches a string `tags` value, diverging from `get_tag_counts`

Status: IMPLEMENTED #1423@c74fbcc
Component: `personal_index/content_analytics.py` — `ContentAnalytics.get_items_by_tag` (lines 81-83); the divergent counterpart `ContentAnalytics.get_tag_counts` (lines 26-34)
Umbrella: ARCH-2 (#983)
Issue: #1400
Docs: `docs/content-analytics.md` (Contract Holes #1)

## Problem
The two tag methods disagree on how they treat a **non-list** `tags` value.

- `get_tag_counts` (line 26) guards with `if isinstance(tags, list)` before
  counting, so a string `tags` value is **ignored**. This is pinned by the
  existing deep test `test_non_list_tags_ignored`
  (`{"tags": "not-a-list"}` → `get_tag_counts() == {"a": 1}`, the string
  contributes nothing).
- `get_items_by_tag` (line 81) does `tag in (item.get("tags") or [])` with
  **no `isinstance` guard**. When `tags` is a **string**, Python's `in`
  operator performs **substring matching**: `"a" in "abc"` is `True`. So an
  item with `tags="abc"` **matches** `get_items_by_tag("a")`, `("b")`, and
  `("c")` — the very value that `get_tag_counts` ignores.

Consequence: the two tag methods give contradictory answers for the same item.
For `a.add_items([{"id": 1, "tags": "abc"}])`:
- `a.get_tag_counts()` → `{}` (the string is ignored).
- `a.get_items_by_tag("a")` → `[{"id": 1, "tags": "abc"}]` (substring match).

A caller that filters items by tag and then reports tag counts (or vice versa)
sees items that "have tag `a`" that the tag-count/distribution/unique-count
methods claim do not exist. This is a genuine correctness divergence, not a
stylistic one: substring matching on a tag field is almost certainly
unintended. This is the same "two methods disagree on the same input" class as
ARCH-66/67/68.

## Public contract (target)
The two tag methods must agree on how they treat a non-list `tags` value.
Preferred option (guard `get_items_by_tag` to match `get_tag_counts`):
1. Reword the `get_items_by_tag` docstring (lines 81-83) to state precisely
   that a non-list `tags` value is **ignored** (matching `get_tag_counts`),
   and that a list `tags` value is matched by exact membership.
2. Change the body to guard with `isinstance(tags, list)` before the
   membership test, e.g.:
       return [item for item in self._items
               if isinstance(item.get("tags"), list) and tag in item["tags"]]
   (equivalently: `tags = item.get("tags") or []; if isinstance(tags, list)
   and tag in tags`). A missing key, `None`, and a non-list value all yield
   no match — identical to `get_tag_counts`.
3. Add ONE pinning test that feeds a string `tags` value and asserts both
   methods agree (see Pinning tests).
4. The existing deep tests `test_non_list_tags_ignored`,
   `test_get_items_by_tag_returns_matching`,
   `test_get_items_by_tag_missing_tags_key`, and
   `test_get_items_by_tag_none_tags_key` remain correct and must NOT change.

Alternative option (document the substring behavior as intended):
5. Reword the `get_items_by_tag` docstring to state explicitly that a string
   `tags` value is matched by substring (and that `get_tag_counts` ignores it),
   and add ONE pinning test that pins the substring behavior. This is NOT
   preferred — it cements a divergence that is almost certainly unintended.

Option 1 is preferred: it makes the two methods agree, is a small additive
change, and matches the already-pinned `get_tag_counts` behavior.

## Behavior
- `get_items_by_tag(tag)` on a **list** `tags` value: unchanged — exact
  membership (`tag in tags`), in insertion order.
- `get_items_by_tag(tag)` on a **missing** `tags` key or `None`: unchanged —
  no match (the `or []` normalization).
- `get_items_by_tag(tag)` on a **non-list** `tags` value (e.g. a string):
  **Option 1 (preferred):** no match (ignored, matching `get_tag_counts`).
  **Option 2:** substring match (documented as intended).
- `get_tag_counts` / `get_tag_distribution` / `get_unique_tags_count`:
  unchanged in both options (they already ignore non-list `tags`).

## Guard inputs
- An empty store: `get_items_by_tag("a")` → `[]` (nothing to match — the
  guard path for the pinning test).
- A missing `tags` key: `{"id": 1}` → no match (regression guard, already
  pinned by `test_get_items_by_tag_missing_tags_key`).
- A `None` `tags` value: `{"id": 1, "tags": None}` → no match (regression
  guard, already pinned by `test_get_items_by_tag_none_tags_key`).
- A **string** `tags` value: `{"id": 1, "tags": "abc"}` → the divergence
  input (Option 1: no match; Option 2: substring match).
- A **list** `tags` value with a match: `{"id": 1, "tags": ["a"]}` → matches
  `get_items_by_tag("a")` (regression guard, already pinned by
  `test_get_items_by_tag_returns_matching`).

## Acceptance criteria
1. `get_items_by_tag("a")` on `{"id": 1, "tags": "abc"}` → `[]` (Option 1) —
   the string `tags` value is ignored, matching `get_tag_counts`.
2. `get_tag_counts()` on `{"id": 1, "tags": "abc"}` → `{}` (unchanged — the
   string is ignored).
3. For the same string-`tags` item, `get_items_by_tag("a")` and
   `get_tag_counts` now **agree**: the item is neither counted nor matched.
4. `get_items_by_tag("a")` on `{"id": 1, "tags": ["a"]}` → `[{"id": 1,
   "tags": ["a"]}]` (list membership unchanged).
5. `get_items_by_tag("a")` on `{"id": 1}` and `{"id": 1, "tags": None}` →
   `[]` (missing/None unchanged).
6. The `get_items_by_tag` docstring states the exact non-list handling
   (ignored in Option 1 / substring in Option 2) and no longer implies
   substring matching when Option 1 is chosen.

## Pinning tests to add
- `test_get_items_by_tag_string_tags_ignored` (Option 1) /
  `test_get_items_by_tag_string_tags_substring` (Option 2): add one item with
  `tags="abc"`; assert `get_items_by_tag("a")` is `[]` (Option 1) or
  `[item]` (Option 2). This is the divergence pin — it exercises the real
  `get_items_by_tag` entry point and asserts the non-list handling against the
  returned list, not the docstring wording.
- `test_get_items_by_tag_and_tag_counts_agree_on_string_tags`: add one item
  with `tags="abc"`; assert `get_items_by_tag("a") == []` AND
  `get_tag_counts() == {}` — one test pins that the two methods agree on the
  same input (the core of the hole).
- `test_get_items_by_tag_empty_store_returns_empty_list` (guard path): an
  empty store returns `[]` for `get_items_by_tag("a")` — nothing to match.
- `test_get_items_by_tag_list_membership_unchanged` (regression guard): with
  `{"id": 1, "tags": ["a"]}`, `get_items_by_tag("a")` returns the item and
  `get_items_by_tag("b")` returns `[]` — list membership is unchanged.
- **Option 2 only:** leave the existing deep tests unchanged (they already pin
  the list/missing/None behavior). **Option 1:** leave them unchanged too
  (they remain correct after the guard is added).

## Docs update (same PR)
`docs/content-analytics.md` — Contract Holes #1 already documents the
substring-match hole. After the fix, update the `get_items_by_tag` section to
state the enforced non-list contract (Option 1: "a non-list `tags` value is
ignored, matching `get_tag_counts`" — or Option 2: "a string `tags` value is
matched by substring") and remove/adjust the Contract Holes #1 callout once
merged.
