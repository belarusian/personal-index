# TICKET-394 — importer.py _import_json placeholder docstring (class-(b) doc-drift)

Status: OPEN

## File
personal_index/importer.py

## Symptom
Importer._import_json (line 84) carries the blanket docstring
"Import from JSON format." which does not enumerate the actual sub-components
the body performs. It is a generic single-line placeholder (class-(b)
doc-drift): it names the format but not the behavior.

## Evidence (line 84, body 85-113)
The body performs four distinct sub-components the docstring does not state:
1. JSON-decode content; on JSONDecodeError append "Invalid JSON: ..." to
   result.errors and return early (no items processed).
2. Normalize a top-level JSON object (dict) into a single-element list so the
   loop treats dict and list inputs uniformly.
3. Per-item: if bookmark.url is non-empty, self._manager.add(bookmark) and
   increment result.total_imported; if empty, increment result.total_skipped
   (no manager write).
4. Per-item (ValueError, TypeError) (raised during Bookmark(...) or
   manager.add) is caught, appended to result.errors as
   "Error importing item: ...", and the loop CONTINUES to the next item (no
   abort).

Existing tests (test_import_json_list / _single_dict / _invalid / _empty_url /
_with_all_fields) cover sub-components 1-3 but NOT sub-component 4 (the
per-item error-accumulation branch that keeps the loop alive).

## Minimal additive fix
- Reword the docstring to enumerate the four sub-components above (exact
  conditionals, not a blanket adjective).
- Add ONE pinning behavior test that monkeypatches Importer._manager.add to
  raise TypeError for one item and asserts on the returned ImportResult:
  total_imported counts only the good item, errors has exactly one
  "Error importing item:" entry, and the loop did not abort (the good item was
  still imported). This witnesses the corrected claim as doc-only.

## Issue
Issue: #626
