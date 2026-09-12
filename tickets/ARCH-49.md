# ARCH-49: content-digest — the summary's item count double-counts multi-tag entries and is decoupled from total_entries

Status: CLAIMED (cycle 253, impl253/content-digest-summary-count)
Component: `personal_index/content_digest.py`
Issue: #1146
Refs: ARCH-2 (#983 umbrella)

## Symptom

`DigestGenerator.generate` states that `total_entries` is the "count of
accumulated entries" and that "a one-line summary is generated from the
sections", but it states **no relationship between the two**, and the two
quantities are computed from different sources and disagree in the default
(`group_by="tags"`) path:

- `total_entries = len(entries)` — the count of **distinct** accumulated
  entries (each entry counted once).
- The summary's `total = sum(s.count for s in sections)` — the sum of the
  **per-section** counts.

In `_group_by_tags`, an entry with `k` tags is appended to `k` different tag
buckets, so it is counted `k` times in `sum(s.count)`. Concretely:

- **Inflation:** an entry tagged `["a", "b"]` (and no other entries) yields
  two sections of one entry each, so the summary reads `"2 new items across 2
  topics: a, b"` while `total_entries` is `1`. The summary reports more items
  than the digest actually contains.
- **Deflation:** the per-section cap (`max_entries_per_section`, default 10)
  truncates each bucket independently, so `sum(s.count)` can also fall **below**
  `total_entries` when a single tag holds more than the cap (e.g. 15 entries
  all tagged `"a"` → one section of 10 → summary says `"10 new items"` while
  `total_entries` is `15`).

The `group_by="source"` path does not inflate (each entry lands in exactly one
bucket), but it still deflates under the cap, so the summary and
`total_entries` can disagree there too. Because the `generate` docstring and
`docs/content-digest.md` make no promise that the summary's number equals
`total_entries`, a caller cannot tell from the contract that the headline
"N new items" figure is a per-section sum (double-counting multi-tag entries
and capping per section) rather than the distinct-entry count. This is the
single most important hole: the digest's headline number is silently wrong for
the ordinary multi-tag input in the default grouping, and the contract gives
no way to know which of the two counts is authoritative.

## Public contract (the fix must preserve the happy path)

- All public methods keep their current signatures and behavior:
  `DigestEntry.to_dict`, `DigestSection.count` (property),
  `ContentDigest.to_dict` / `format_markdown` / `format_text`,
  `DigestGenerator.__init__` / `add_entry` / `add_entries` / `generate` /
  `clear`, and the private `_resolve_sections` / `_group_by_tags` /
  `_group_by_source` / `_generate_summary`.
- The relationship between the summary's item count and `total_entries` must
  be made explicit (pick one and state it in the `generate` docstring +
  `docs/content-digest.md`):
  - **Option A (summary equals total_entries):** compute the summary's `total`
    from the distinct-entry count (pass `len(entries)` into
    `_generate_summary` or derive it there) so the headline "N new items"
    always equals `total_entries`. The per-section grouping and cap are
    unchanged; only the summary's number changes.
  - **Option B (document the per-section sum):** keep the summary's `total` as
    `sum(s.count for s in sections)` and state explicitly in the `generate`
    docstring and `docs/content-digest.md` that the summary's number is the
    sum of the per-section (capped) counts, that it intentionally differs from
    `total_entries` in the multi-tag (inflation) and over-cap (deflation)
    cases, and that `total_entries` is the authoritative distinct-entry count.
- Whichever option is chosen, the postcondition must hold and be stated: a
  caller reading the `generate` docstring must know, without reading the
  source, whether the summary's "N new items" figure equals `total_entries` or
  is a per-section sum, and which figure is authoritative.

## Acceptance criteria

1. The happy path is unchanged: `generate` behaves exactly as documented in
   `docs/content-digest.md` for `group_by` in `{"tags", "source", "none"}`,
   including the score-descending sort, the per-section cap, the
   `"Uncategorized"` section for untagged entries, the `"Unknown"` source
   bucket, the default period (`now - 7 days` to `now`), and the
   `"No new content found."` summary for empty input.
2. The relationship between the summary's item count and `total_entries` is
   stated in the `generate` docstring and in `docs/content-digest.md`
   (Option A: the summary's number always equals `total_entries`; Option B:
   the summary's number is the per-section capped sum and `total_entries` is
   the authoritative distinct-entry count).
3. If Option A: a digest with a multi-tag entry (e.g. one entry tagged
   `["a", "b"]`) reports the same "N new items" figure in the summary as
   `total_entries` (1, not 2), and a digest with 15 entries all in one tag
   reports 15, not 10.
4. If Option B: the docstring and the docs page both state that the summary's
   number is the per-section capped sum and that `total_entries` is the
   authoritative distinct-entry count, and no caller-facing API implies the
   two are equal.

## Pinning tests to add (tests/test_content_digest.py)

- `test_generate_single_untagged_entry` (happy path) — one entry with no tags
  and `group_by="tags"` yields one `"Uncategorized"` section,
  `total_entries == 1`, and a summary whose item count is 1; pins the
  current happy-path shape so the fix does not change clean single-tag input.
- `test_generate_multi_tag_entry_summary_count` (the contract hole) — one
  entry tagged `["a", "b"]` (and no other entries) with `group_by="tags"`
  yields two sections (`"a"`, `"b"`) each of count 1, `total_entries == 1`,
  and a summary whose "N new items" figure equals `total_entries` under
  Option A (1) OR, under Option B, the documented per-section sum (2) with the
  docstring stating `total_entries` is authoritative. This single test pins
  the whole contract hole.
- `test_generate_over_cap_summary_count` (guard path) — 15 entries all tagged
  `"a"` with `max_entries_per_section=10` yields one section of 10,
  `total_entries == 15`, and a summary whose item count is 15 under Option A
  OR the documented per-section sum (10) under Option B; pins the deflation
  case alongside the inflation case so one returned digest pins both
  directions of the divergence.

## Docs update (same PR)

`docs/content-digest.md` "Contract Holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the
`DigestGenerator.generate` entry in the "Public API" section to state the
chosen summary-vs-total_entries relationship once implemented.
