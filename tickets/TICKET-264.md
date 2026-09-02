# TICKET-264: SearchIndex._load — unguarded json.load allows non-dict top-level type

## File
`personal_index/index.py` (line 51, `_load` method)

## Symptom
When the storage file contains valid JSON that is not a dict (null, list, number),
`json.load` succeeds but the subsequent `data.get("pages", {})` raises
`AttributeError` which is NOT caught by the existing except clause.

## Evidence
null: AttributeError NoneType has no attribute get
list: AttributeError list has no attribute get
number: AttributeError int has no attribute get
Reproduced live in cycle 19.

## Minimal Additive Fix
Add isinstance(data, dict) guard after json.load; if not dict, reset to empty state.

## Status
RESOLVED

Issue: #357
