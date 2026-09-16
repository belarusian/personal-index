# ARCH-69 — content_changelog: `get_entries` returns a shallow copy — entry objects and `details` dicts are shared references, so mutating a returned entry corrupts the stored entry

Status: CLOSED (architect close, cycle 280; verified by validator) #1422@16e7861 (validator cycle 223: Option 1 shallow-copy contract confirmed; 22 AC+adversarial deep tests in tests/deep/test_content_changelog_arch69_verify.py, 73 targeted green; docs/content_changelog.md Contract Hole 1 callout still stale - architect follow-up)
Component: `personal_index/content_changelog.py` — `ContentChangelog.get_entries` (lines 29-46); the `ChangeEntry` dataclass (lines 10-17)
Umbrella: ARCH-2 (#983)
Issue: #1394
Docs: `docs/content_changelog.md` (Contract Holes #1)

## Problem
`ContentChangelog.get_entries(url=None)` (line 29) has a docstring that says it
returns "A NEW list of ``ChangeEntry`` objects (a copy, not the internal
list)". That is **true only of the list container**. The body is:

    if url:
        return [e for e in self._entries if e.url == url]
    return list(self._entries)

Both branches return a **shallow** copy: a new `list`, but the `ChangeEntry`
objects inside it are the **same objects** held by `self._entries`, and each
entry's `details` dict is the **same dict** object. This is already pinned by
the existing deep tests `test_entry_identity_preserved_in_get`
(`assert entries[0] is e`) and `test_details_dict_is_shared_reference`
(`assert entries[0].details is details`) in
`tests/deep/test_content_changelog_adversarial.py`.

Consequence: the "a copy, not the internal list" wording over-promises safety.
A caller that mutates a returned entry corrupts the internal store (verified
against the code):
- `cl.get_entries()[0].details["k"] = "v"` → the **stored** entry's `details`
  now contains `"k": "v"` (same dict object).
- `cl.get_entries()[0].change_type = "tampered"` → the **stored** entry's
  `change_type` is now `"tampered"` (same object).
- `cl.get_entries("http://x.com")[0].url = "http://y.com"` → the stored
  entry's `url` changes, so a subsequent `get_entries("http://x.com")` no
  longer matches it.

The docstring reads as "mutating the result is safe," which is false for the
entry objects and their `details` dicts. This is the same "advertised safety
not actually provided" class as ARCH-66/67/68.

## Public contract (target)
The docstring, the code, and the tests must all agree on whether `get_entries`
returns a shallow or a deep copy. Two options; pick ONE and make all three
agree:

Preferred option (reword the docstring to the exact truth — shallow copy):
1. Reword the `get_entries` docstring (lines 30-43) to state precisely that
   the **list** is a new shallow copy but the **`ChangeEntry` objects and
   their `details` dicts are shared references** — mutating a returned entry
   or its `details` dict mutates the stored entry. Remove the blanket "a
   copy, not the internal list" phrasing that implies entry-level safety.
2. Add ONE pinning test that mutates a returned entry's `details` dict and
   asserts the stored entry is affected (see Pinning tests).
3. The existing deep tests `test_entry_identity_preserved_in_get` and
   `test_details_dict_is_shared_reference` already pin the shared-reference
   behavior and remain correct — do NOT change them.

Alternative option (make it a deep copy so the "copy" wording is true):
4. Change `get_entries` to return deep copies: new `ChangeEntry` objects with
   copied `details` dicts (e.g. `dataclasses.replace(e, details=dict(e.details))`
   or an explicit copy) in both branches.
5. Update the two existing deep tests that currently pin the shared-reference
   behavior (`test_entry_identity_preserved_in_get`,
   `test_details_dict_is_shared_reference`) to pin the copy behavior instead
   (`entries[0] is not e`, `entries[0].details is not details`).
6. Add the same pinning test as option 1, but asserting the stored entry is
   NOT affected by mutating the returned entry.

Option 1 is preferred: it is a doc-only change (no behavior change, no risk to
the existing 538-line deep-test suite) and makes the documented contract match
the observed behavior.

## Behavior
- `get_entries()` / `get_entries(url)` returns a **new list** in both branches
  (unchanged — the list container is always a fresh object).
- **Option 1 (shallow, preferred):** mutating a returned entry's `details`
  dict or scalar field mutates the stored entry (shared reference). The
  docstring now states this explicitly.
- **Option 2 (deep):** mutating a returned entry's `details` dict or scalar
  field does NOT affect the stored entry (independent copies).
- The filter semantics are unchanged in both options: truthy `url` → exact
  `e.url == url` match; falsy `url` (`None`/`""`) → all entries; empty
  changelog → `[]`.

## Guard inputs
- An empty changelog: `get_entries()` and `get_entries("http://x.com")` both
  return `[]` (nothing to mutate — the guard path for the pinning test).
- A falsy `url` (`None` and `""`): returns all entries (regression guard: the
  falsy branch is also a shallow copy in option 1 / deep copy in option 2).
- A truthy `url` with a match: returns the filtered subset (the divergence
  input — the returned entry shares the stored object in option 1).
- A truthy `url` with no match: returns `[]` (regression guard).

## Acceptance criteria
1. `get_entries()` returns a new list object: `cl.get_entries() is not
   cl.get_entries()` (regression guard: the list container is always fresh).
2. **Option 1:** after `cl.add_entry(e)`, `cl.get_entries()[0].details["k"] =
   "v"` → `cl.get_entries()[0].details == {"k": "v"}` (the stored entry is
   affected). **Option 2:** the same mutation → the stored entry's `details`
   is unchanged (`{}`).
3. **Option 1:** `cl.get_entries()[0] is e` (shared object). **Option 2:**
   `cl.get_entries()[0] is not e` (independent copy).
4. The `get_entries` docstring states the exact copy semantics (shallow in
   option 1 / deep in option 2) and no longer implies entry-level safety when
   the copy is shallow.
5. The filter semantics are unchanged: truthy `url` → exact match only; falsy
   `url` → all entries; empty changelog → `[]` in both branches.

## Pinning tests to add
- `test_get_entries_shallow_copy_details_shared` (option 1) /
  `test_get_entries_deep_copy_details_independent` (option 2): add one entry
  with a `details` dict; call `get_entries()`; mutate the returned entry's
  `details` dict; assert the stored entry IS affected (option 1) or is NOT
  affected (option 2). This is the divergence pin — it exercises the real
  `get_entries` entry point and asserts the copy semantics against the stored
  object, not the docstring wording.
- `test_get_entries_empty_changelog_returns_empty_list` (guard path): an empty
  changelog returns `[]` for both `get_entries()` and
  `get_entries("http://x.com")` — nothing to mutate, the guard path.
- `test_get_entries_falsy_url_returns_all_shallow` (option 1) /
  `test_get_entries_falsy_url_returns_all_deep` (option 2): with two entries,
  `get_entries(None)` and `get_entries("")` each return both entries; assert
  the shared-reference (option 1) or independent-copy (option 2) semantics on
  the falsy branch too.
- **Option 2 only:** update the two existing deep tests
  `test_entry_identity_preserved_in_get` and `test_details_dict_is_shared_reference`
  to pin the copy behavior (`is not` / `is not`). **Option 1:** leave them
  unchanged (they already pin the shared-reference behavior).

## Docs update (same PR)
`docs/content_changelog.md` — Contract Holes #1 already documents the
shallow-copy hole. After the fix, update the `get_entries` section to state
the enforced copy contract (shallow: "the list is a new shallow copy; the
`ChangeEntry` objects and their `details` dicts are shared references" — or
deep: "returns independent copies of each entry and its `details` dict") and
remove/adjust the Contract Holes #1 callout once merged.
