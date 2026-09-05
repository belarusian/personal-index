# TICKET-459: ValidationResult.to_dict blanket "Convert to dictionary" (class-(b) doc-drift)

- File: personal_index/content_validation.py
- Function: ValidationResult.to_dict (line 70)
- Symptom: one-line generic docstring `"""Convert to dictionary."""` that does not
  enumerate the 6 keys returned, the derived `error_count`/`warning_count` (len of
  the respective lists), or the fact that `errors` is a projected list of
  `{field, message}` dicts (not the full ValidationError objects with severity/value).
- Evidence (line 71): `"""Convert to dictionary."""`
- Body performs: returns a dict with keys `is_valid`, `error_count` (len(errors)),
  `warning_count` (len(warnings)), `items_valid`, `items_invalid`, and `errors`
  (a list of `{"field": e.field, "message": e.message}` for each error — a
  projection that drops severity and value). The `warnings` list is NOT included
  in the output (only its count).
- Minimal additive fix: reword the docstring to enumerate the 6 keys, the derived
  counts, and the errors projection (NO behavior change). Add ONE pinning test
  `test_to_dict_pins_keys_and_projection` (normal: result with 1 error + 1 warning
  → verify all 6 keys, error_count=1, warning_count=1, errors is a list of
  {field, message} dicts without severity/value; guard: empty result → error_count=0,
  warning_count=0, errors=[]).
- Status: OPEN
- Issue: #760
