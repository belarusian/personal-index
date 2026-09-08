# ARCH-27: content_reader — duplicate URLs make `get` and the collection views disagree

- **Status:** OPEN
- **Component:** `personal_index/content_reader.py` (`ContentReader`)
- **Docs:** `docs/content-reader.md` (contract hole 1)
- **Issue:** #<n> (created at triage)
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
3. `docs/content-reader.md` contract hole 1 is resolved (the page no longer
   lists it as an open hole, or the hole text is updated to the chosen
   policy).

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

## Docs update (same PR)
`docs/content-reader.md` — update contract hole 1 to reflect the chosen
policy (remove it from the open-holes list once the behavior is pinned).
