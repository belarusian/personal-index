# TICKET-303: serializer.from_json annotation/docstring promise dict but returns any JSON type

- Status: RESOLVED
- Module: personal_index/serializer.py
- Defect class: (b) doc/behavior drift
- Issue: #439

## Symptom
`Serializer.from_json` is annotated `-> dict` and its docstring promises
"Deserialize JSON string to dict." `json.loads` returns ANY JSON top-level
type, so a caller that trusts the annotation (or mypy, which trusts it
unconditionally) will treat a list/str/int/None as a dict and crash later,
far from the parse site.

Note: gh #439 names the class `DataSerializer`; the real class on main is
`Serializer` (personal_index/serializer.py:36). Same method, corrected here.

## Evidence
- Site: personal_index/serializer.py:54-59 - `def from_json(self, json_str: str) -> dict:`
  / `"""Deserialize JSON string to dict."""` / `result = json.loads(json_str)`
  / `return result  # type: ignore[no-any-return]`.
- Runtime (verified on d44b500): `Serializer().from_json('[1,2]')` -> `list`,
  `'"str"'` -> `str`, `'42'` -> `int`, `'null'` -> `NoneType`. None of these
  is a dict; none raises.
- Contrast: `to_dict` (line 80) legitimately returns `dict`; `from_json` does not.

## Minimal additive fix
No behaviour change (the code is correct - it is the contract that is wrong):
1. Annotate `-> Any` and drop the now-unneeded `# type: ignore[no-any-return]`.
2. Correct the docstring to state the return is any JSON top-level type and
   that callers needing a dict must check `isinstance(result, dict)`.
3. Regression tests in tests/test_serializer.py asserting list/str/int/None
   round-trip out of `from_json` unchanged, and that `DeserializationError`
   still fires for malformed input (existing contract preserved).

## Out of scope
No runtime type guard, no signature change, no new exception - callers such
as tests/test_exception_chains.py:34 depend on the current error contract.

## Resolution
Merged to main as squash commit 1e43620 (PR #440, CI run 33758779336 green on 3.10/3.11/3.12).
gh issue #439 closed. Cycle 59.
