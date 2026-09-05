# TICKET-445: content_validation.py ContentValidator.validate docstring over-promises (blanket)

Status: RESOLVED
Issue: #728
Module: personal_index/content_validation.py
Method: ContentValidator.validate
Symptom: class-(b) doc-drift - blanket docstring
Evidence: line 108 `"""Validate a list of content items."""`

## Detail
The `validate` docstring is a one-line blanket claim that does not enumerate:
- the per-item checks it runs via `_validate_item` (required fields, URL,
  title, score, dates)
- that a title-length breach is a WARNING (does not mark the item invalid),
  whereas required-field / URL / score-type / date breaches are ERRORS
- that it tallies `items_valid` / `items_invalid` per item
- the returned `ValidationResult` fields: is_valid, errors, warnings,
  items_valid, items_invalid

## Minimal additive fix
Reword the docstring to state the EXACT behavior (enumerate the per-item checks,
the warning-vs-error distinction, the items_valid/items_invalid tally, and the
returned ValidationResult fields). Add ONE pinning test that pins the RETURNED
OBJECT fields for both the normal case (all-valid item: is_valid True, no
errors/warnings, items_valid 1) and the guard path (a title-length breach
surfaces a WARNING but leaves the item valid, vs a required-field breach that
marks it invalid).
