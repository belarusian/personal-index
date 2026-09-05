# TICKET-443: DigestGenerator.generate docstring omits parameter defaults and return structure

Status: RESOLVED
Module: personal_index/content_digest.py
Function: DigestGenerator.generate (line 147)

## Symptom
The `generate` docstring (lines 155-161) states only that entries are sorted by
score (descending), grouped by the `group_by` strategy, and each section is
capped at `max_entries_per_section` (default 10). It does NOT enumerate:
- the `title` parameter (default `"Content Digest"`),
- the `period_start` default (7 days before now, ISO-8601 UTC),
- the `period_end` default (now, ISO-8601 UTC),
- the returned `ContentDigest` structure (title, generated_at, period_start,
  period_end, sections, total_entries, summary).

This is a class-(b) doc-drift: the docstring under-specifies the actual
behavior the body performs.

## Evidence
personal_index/content_digest.py lines 147-175:
- signature: `generate(self, title="Content Digest", period_start=None,
  period_end=None, group_by="tags", max_entries_per_section=10)`
- body: `period_start or (now - timedelta(days=7)).isoformat()`,
  `period_end or now`, `total_entries=len(entries)`, `summary=self._generate_summary(sections)`
- docstring (155-161) mentions none of the above.

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate all five
parameters with their defaults (title, period_start->7 days ago, period_end->now,
group_by, max_entries_per_section), the sort/group/cap behavior, and the
returned ContentDigest fields. Add ONE pinning test asserting the returned
ContentDigest object fields (period_start ~7 days before period_end, title
default, total_entries, summary) for the default-args case, alongside an
explicit-args case.

## Issue
Issue: #724
