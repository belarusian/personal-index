# ARCH-27: content_reader — duplicate URLs make `get` and the collection views disagree

- **Status:** IMPLEMENTED #1419@c52387c (architect cleared the docs/** blocker, cycle 233: criterion 3 reworded to architect-owned docs reconciliation; implementer re-claims the code+tests half — see tickets/IMPL-7.md, now CLOSED)
- **Component:** `personal_index/content_reader.py` (`ContentReader`)
- **Docs:** `docs/content-reader.md` (contract hole 1)
- **Issue:** #1073
- **Carry-forward:** part of ARCH-2 (#983) — the docs-coverage umbrella.

## Symptom
`ContentReader.add` appends every item to `_items` (insertion order) but
overwrites `_url_index[item.url] = item` (last-write-wins). After adding two
items with the same URL:

- `count`, `list_all`, `paginate`, `filter_by_tags`, `filter_by_score`,
  `search_titles`, `search_content` all iterate `_items` and therefore see
  **both** items.
- `get(url)` reads `_url_index` and returns only the **last** item added for
  that URL.

So the URL — documented as the lookup key ("Get a content item by URL") — is
not a consistent key: `get(url)` and `list_all()` are internally inconsistent
for repeated URLs. There is no dedup, no error, and no documented
last-write-wins policy.

## Evidence (live code, `personal_index/content_reader.py`)

    def add(self, item: ReadResult) -> None:
        """Add a content item."""
        self._items.append(item)          # both items kept
        self._url_index[item.url] = item  # last item wins

    def get(self, url: str) -> ReadResult | None:
        """Get a content item by URL."""
        return self._url_index.get(url)   # only the last one

`list_all` returns `list(self._items)` (both); `count` returns
`len(self._items)` (2). No test pins the duplicate-URL case.

## Public contract (what the fix must satisfy)
Pick ONE coherent policy and make `get` and the collection views agree:
- **Option A (dedup on add):** `add` replaces an existing item with the same
  URL in place (or rejects it), so `_items` and `_url_index` always hold at
  most one item per URL. `count`/`list_all`/`get` then agree.
- **Option B (document last-write-wins + make `get` consistent):** keep both
  in `_items` but document that `get(url)` returns the most-recently-added
  item for that URL, and ensure every collection view that is "by URL"
  reflects the same policy.

Whichever option is chosen, the docstring of `add` and `get` must state the
duplicate-URL behavior explicitly (no silent divergence).

## Acceptance criteria
1. After `add(a)` then `add(b)` with `a.url == b.url`, `get(a.url)` and the
   collection views (`count`, `list_all`, `paginate`) are mutually
   consistent under one documented policy.
2. `add`/`get` docstrings state the duplicate-URL behavior.
3. (ARCHITECT-OWNED — not part of the implementer's acceptance.) The
   `docs/content-reader.md` contract-hole-1 reconciliation is performed by the
   ARCHITECT in a follow-up (or in the same PR by the architect), NOT by the
   implementer: the page no longer lists contract hole 1 as an open hole, or
   the hole text is updated to the chosen policy. The implementer's acceptance
   is met in code+tests alone (criteria 1-2); the docs/** path is architect-
   owned and the implementer is structurally forbidden to write it (same shape
   as ARCH-26 / cycle 234).

## Pinning tests to add (in `tests/test_content_reader.py`)
- `test_duplicate_url_get_returns_last`: add two items with the same URL;
  assert `get(url)` returns the **last** added item (pins the current
  last-write-wins behavior, or the new dedup behavior once chosen).
- `test_duplicate_url_count_and_list_all`: add two items with the same URL;
  assert `count` and `len(list_all())` agree with the chosen policy (1 under
  dedup, 2 under last-write-wins) and that `get(url)` is consistent with them.
- Guard path: a single-URL reader still returns that item from `get` and
  `count == 1` (the normal case, so one test pins both the main behavior and
  the no-duplicate guard).

## Docs update (ARCHITECT-OWNED — not in the implementer's PR)
`docs/content-reader.md` — the contract-hole-1 reconciliation is an ARCHITECT
task (docs/** is architect-owned; the implementer cannot write it). Once the
implementer lands the code+tests half (criteria 1-2) and the behavior is
pinned, the architect updates contract hole 1 to reflect the chosen policy
(remove it from the open-holes list, or reword the hole text to the chosen
policy). This is the sole reason IMPL-7 was raised and is now cleared.
