# TICKET-388: sitemap_builder.py placeholder docstrings (class-(b) doc-drift)

Status: OPEN

## File
personal_index/sitemap_builder.py

## Symptom
Two methods carry generic `"""Process <name>.` placeholders that do not
describe the exact behavior the bodies perform:
- `SitemapBuilder.add_entry` (line 51): constructs a `SitemapEntry` from the
  four arguments (url, last_modified, change_frequency, priority) and appends
  it to `self.entries`; returns None.
- `SitemapBuilder.add_entries` (line 65): extends `self.entries` in place with
  the passed `entries` list (no copy / de-duplication); returns None.

## Evidence
- L58: `"""Process add_entry.` — body:
  `self.entries.append(SitemapEntry(url, last_modified, change_frequency, priority))`.
- L66: `"""Process add_entries.` — body: `self.entries.extend(entries)`.

## Minimal additive fix
Reword each placeholder to state the exact behavior the body performs. Add
ONE pinning behavior test: `add_entry` stores the exact `change_frequency` and
`priority` passed on the appended `SitemapEntry` (the corrected claim), and
assert the sibling `last_modified` is the auto-filled default (absent from the
caller's arguments) so the doc-only fix is witnessed.

Issue: #614

## Status
OPEN
