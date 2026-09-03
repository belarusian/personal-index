# TICKET-301: cycle_signals.load_codemap leaks raw JSONDecodeError / returns non-dict

- Status: RESOLVED
- Module: personal_index/cycle_signals.py
- Class: unguarded `json.loads` + missing non-dict guard (violates the module's own CLI error style)
- Issue: #434

## Symptom
`load_codemap()` (personal_index/cycle_signals.py:344-349) is the single entry point for
reading a codemap JSON file, and it already carries an error contract for a bad file: the
missing-file branch prints `[signal] ERROR: ...` to stderr and calls `sys.exit(1)`. The two
CONTENT failure modes bypass that contract:

1. Malformed JSON -> raw `json.JSONDecodeError` escapes as an unhandled traceback instead of
   the module's `[signal] ERROR:` line plus exit 1.
2. Valid JSON that is not an object (e.g. a top-level array) -> returned as-is despite the
   `-> dict` annotation; every downstream consumer (`extract()` at line 535, the `--diff`
   path at line 578) then calls `codemap.get(...)`, so the failure surfaces much later as an
   `AttributeError`, far from the cause.

## Evidence
Repro (corrupt file): RAW LEAK: JSONDecodeError Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
Repro (top-level array): returned type: list value: [1, 2, 3]

Existing tests cover only the happy path and the missing-file path
(tests/test_cycle_signals.py:454-463, TestLoadCodemap) - neither content failure mode is
asserted. `cycle_signals` is NOT in the closed corrupt-JSON-guard class (bookmarks /
content_search / analytics / session / backup) - this is a new instance in an uncovered module.

## Minimal additive fix
Keep the signature and the missing-file branch untouched; wrap the parse in
`except json.JSONDecodeError` and add an `isinstance(data, dict)` guard, both reporting
through the module's existing style (print to stderr + sys.exit(1)). The trailing
`# type: ignore[no-any-return]` becomes unnecessary once the dict guard is in place.

## Tests
TestLoadCodemap::test_load_malformed_json_exits and
TestLoadCodemap::test_load_non_dict_json_exits - assert SystemExit, and that no
JSONDecodeError escapes the malformed case.
