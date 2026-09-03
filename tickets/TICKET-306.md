# TICKET-306

- Status: OPEN
- Module: personal_index/storage.py
- Defect class: (a) unguarded exception / crash on corrupt input
- Issue: #445

## Symptom
`Storage._read_json` (personal_index/storage.py:29-35) calls `json.loads(content)` with no
guard. When any of the three backing files (interests.json / config.json / pages.json) on
disk contains malformed JSON, every public accessor that routes through it raises a raw
`json.JSONDecodeError` traceback instead of degrading to the documented default.

Repro on 0a5b99: write `{not json` into interests.json, config.json and pages.json, then
call `get_interests()` / `get_config()` / `get_pages()` -> all three raise JSONDecodeError.

## Evidence
- Site: personal_index/storage.py:29-35 (`return json.loads(content)` on line 35).
- _read_json is the ONLY json parse in the module; all 9 public accessors route through it
  (grep -n _read_json -> lines 44,58,72,103,112,126,140,150).
- The module own contract proves corruption must be non-fatal: _ensure_files() seeds
  []/{}/[]; an empty/whitespace file already returns [] (interests/pages) or {} (config);
  and every caller already degrades on a *type* mismatch (if not isinstance(data, list):
  return []). Only *malformed* content escapes as a traceback.

## Minimal additive fix
Wrap the parse in `except json.JSONDecodeError` and return the same default _read_json
already uses for an empty file: list-default for interests.json / pages.json, dict-default
otherwise. No signature or return-type change, no new module, no CLI/exit-code change.

## Tests
Extend tests/test_storage.py with corrupt-JSON regressions for all three files plus a
whitespace-only case, asserting the documented default is returned and no JSONDecodeError
escapes.
