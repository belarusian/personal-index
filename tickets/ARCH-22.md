Status: VERIFIED (was IMPLEMENTED PR#1248@a696a86; verified cycle 199 @ main ee0efdc)
Kind: ARCH
Author: architect (cycle 184)
Issue: #1060

# ARCH-22: sitemap_builder - `MAX_SITEMAP_SIZE_BYTES` is declared but never enforced

## Component
`personal_index/sitemap_builder.py` (home: `docs/content-sitemap.md`).
One contract hole in the sitemap builder's size-limit constant.

## Symptom

`SitemapBuilder` declares two class constants:

    MAX_URLS_PER_SITEMAP = 50_000
    MAX_SITEMAP_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

`MAX_URLS_PER_SITEMAP` is enforced: it is the default `chunk_size` for
`split_into_chunks`, so a caller who splits before building stays under the
50k-URL limit. `MAX_SITEMAP_SIZE_BYTES` is **never referenced anywhere** in
the module (or the repo): `build()` serializes every entry unconditionally,
and `split_into_chunks()` chunks **only by URL count**, never by the
serialized byte length.

So a sitemap with, e.g., 49,999 URLs each carrying a long `loc` (or a long
`lastmod`) can silently serialize to well over the 50 MB limit the constant
advertises. The constant is dead weight: it documents a limit the code does
not enforce, and a reader who trusts it will assume `build()`/
`split_into_chunks()` respect a byte budget that does not exist.

## Public contract (the fix)

Make the byte limit real (or remove it). Two acceptable shapes (implementer
picks one, states it in the docstring):

- **Option A (enforce):** `split_into_chunks` (or a new
  `split_by_size(max_bytes: int = MAX_SITEMAP_SIZE_BYTES)`) measures the
  serialized length of each entry (e.g. `len(tostring(entry.to_element(),
  encoding="unicode"))` plus the per-entry overhead) and breaks a chunk when
  adding the next entry would exceed `max_bytes`. `build()` then documents
  that it does **not** enforce the limit and that callers must split first.
  The constant becomes load-bearing.
- **Option B (remove):** delete `MAX_SITEMAP_SIZE_BYTES` (it is dead), and
  document in `build()`/`split_into_chunks()` that the only enforced limit is
  the 50k-URL count, so a reader is not misled into expecting a byte budget.

Either way the docstring of `build()` and `split_into_chunks()` must state
explicitly which limits are enforced and which are not, so the constant and
the behavior agree.

## Acceptance criteria
- After the fix, `MAX_SITEMAP_SIZE_BYTES` is either (a) referenced by an
  enforcement path that actually measures serialized bytes, or (b) removed.
- `build()` and `split_into_chunks()` docstrings state exactly which limits
  are enforced (URL count, byte size) and which are not.
- The `docs/content-sitemap.md` "contract holes" section is updated to mark
  hole 1 resolved (or reworded to match the chosen shape).

## Pinning tests to add
- **Option A:** a test that builds a `SitemapBuilder`, adds entries whose
  serialized size exceeds `MAX_SITEMAP_SIZE_BYTES` while staying under
  `MAX_URLS_PER_SITEMAP`, calls the size-aware split, and asserts no chunk
  serializes to more than `MAX_SITEMAP_SIZE_BYTES` bytes.
- **Option B:** a test asserting the constant is gone (e.g. `not
  hasattr(SitemapBuilder, "MAX_SITEMAP_SIZE_BYTES")`) and that `build()` on a
  large-but-under-50k-URL set returns the full serialization with no
  byte-based truncation.
- **Guard path (both options):** a test that `build()` on an **empty**
  builder returns the XML declaration + an empty `<urlset>` (no entries), so
  the zero-entry guard path is pinned alongside the size behavior.

## Docs
`docs/content-sitemap.md` - update the "contract holes" section (hole 1) in
the same PR as the fix.
