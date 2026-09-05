# TICKET-452

- Module: personal_index/content_archive/archiver.py
- Class: ContentArchiver
- Function: archive_old
- Status: OPEN

## Symptom
Doc-drift. The docstring "Archive items older than the threshold." does not
enumerate the exact guard paths the body performs:
  1. Only items whose `archived_at` is non-None are considered. Items added via
     `add_item(..., saved_at=None)` (the default) are NEVER archived, regardless
     of age.
  2. `add_item` stores its `saved_at` parameter into the entry's `archived_at`
     field, so the "age" being compared is the saved_at timestamp, not the
     archive time.
  3. The cutoff is `now - threshold` (threshold = days_threshold arg or
     config.days_threshold); an item is archived only when its parsed
     `archived_at` is strictly before the cutoff.
  4. Unparseable `archived_at` values are silently skipped (ValueError/TypeError
     swallowed).
  5. Returns the list of archived item ids (empty list when none qualify).

## Evidence
- personal_index/content_archive/archiver.py:65-82 (archive_old body:
  `saved_at = entry.archived_at; if saved_at: ... if saved_time < cutoff:`)
- personal_index/content_archive/archiver.py:43-55 (add_item stores saved_at
  into archived_at)

## Minimal additive fix
Reword the `archive_old` docstring to state the exact behavior above (enumerate
the guard paths, the cutoff, the silent-skip, and the return value). NO behavior
change. Add ONE pinning test asserting: an item added without saved_at is NOT
archived, while an item with an old saved_at IS archived.
