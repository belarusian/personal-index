# TICKET-326: content_digest module docstring promises "interests" grouping that no code implements

- File: personal_index/content_digest.py
- Status: RESOLVED
- Class: (b) doc/behavior drift

## Symptom
The module docstring (line 4) promises digests are "grouped by topics and
interests." No interest-based grouping exists anywhere in the module: the word
"interest" appears only in the docstring. `_resolve_sections` (line ~171)
supports only `group_by` values `"none"`, `"source"`, and a default that
delegates to `_group_by_tags`. There is no `_group_by_interests` and no
`group_by="interests"` branch.

## Evidence
- `grep -n interest personal_index/content_digest.py` -> only line 4 (docstring).
- `_resolve_sections` branches: `none` / `source` / default `_group_by_tags`.
- No `interest` field on `DigestEntry`; no interest grouping function.

## Minimal additive fix
Correct the module docstring to describe the grouping actually implemented
(topics/tags and source), removing the unimplemented "interests" claim. Add ONE
regression test asserting the module docstring does not promise an
"interests" grouping capability.

## Issue: #490
