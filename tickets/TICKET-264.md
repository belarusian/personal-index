# TICKET-264: SearchIndex._load — unguarded json.load allows non-dict top-level type

## File
`personal_index/index.py` (line 51, `_load` method)

## Symptom
When the storage file contains valid JSON that is not a dict (null, list, number),
`json.load` succeeds but the subsequent `data.get("pages", {})` raises
`AttributeError` which is NOT caught by the existing `except (json.JSONDecodeError, KeyError, TypeError)` clause.

## EvidenceIssue: #357
