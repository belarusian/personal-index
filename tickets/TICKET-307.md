# TICKET-307: content_importer._import_json escapes raw JSONDecodeError on malformed JSON

- Status: RESOLVED
- Module: personal_index/content_importer.py
- Issue: #448

## Symptom
`ContentImporter().import_content('{not json', 'json')` raises a raw
`json.JSONDecodeError` traceback instead of a clean error. The public
`import_content` contract (line 24) already raises a clean `ValueError` for an
unsupported format (line 28), and `_normalize_items` (line 126) degrades on
missing fields - but *malformed* JSON is the one input that escapes as a
traceback.

## Evidence
- `personal_index/content_importer.py:34` - `parsed = json.loads(data)` is
  unguarded; it is the ONLY json parse in the module.
- `personal_index/content_importer.py:28` - the module's established clean
  error for a caller-level input problem is `ValueError`.
- `tests/test_content_importer.py:182-184` - `test_import_json_invalid`
  currently asserts `json.JSONDecodeError` escapes, locking in the buggy
  behavior.

## Fix (minimal, additive, one function)
Wrap the parse in `_import_json` with `except json.JSONDecodeError` and raise a
clean `ValueError` (matching the module's existing `ValueError` for unsupported
formats). Malformed JSON is a caller-level input error, not a content-level
degradation, so `ValueError` is the matching clean behavior. No
signature/return-type change, no new module, no CLI/exit-code change.

Update `test_import_json_invalid` to assert the clean `ValueError` (and that no
`JSONDecodeError` escapes), and add a malformed-JSON regression test.
