# TICKET-353: content_digest.DigestGenerator.generate docstring drift

**File:** personal_index/content_digest.py
**Function:** DigestGenerator.generate
**Symptom:** Docstring is the blanket claim "Generate a content digest." which omits three real behaviors the body performs: (1) entries are sorted by score descending, (2) grouping is selected by the `group_by` argument ("tags" default, "source", or "none"), and (3) each section is capped at `max_entries_per_section` (default 10) entries.
**Evidence:** Line ~150: `entries = sorted(self._entries, key=lambda e: e.score, reverse=True)`; `_resolve_sections` branches on `group_by` ("none"/"source"/default tags); `_group_by_tags`/`_group_by_source` slice `entries[:max_per_section]`.
**Fix:** Reword the docstring to state the exact sort key/direction, the group_by conditional, and the per-section limit with its default. Add ONE behavior test that pins the corrected claim (per-section cap at the default limit of 10) against the returned ContentDigest object.

## Status: RESOLVED
Merged to main 988fe04, gh #544 closed, PR #545 squash-merged.
