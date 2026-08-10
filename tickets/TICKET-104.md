# TICKET-104: F401 — Unused import `TYPE_CHECKING` in `content_tagger/tagger.py`

## Title
`personal_index/content_tagger/tagger.py` imports `TYPE_CHECKING` but never uses it

## Evidence
File: `personal_index/content_tagger/tagger.py`

Line 6: `from typing import TYPE_CHECKING, Any`

The module imports `TYPE_CHECKING` from `typing` but never references it anywhere in the code.

## Impact
- Dead code that increases cognitive load
- Slightly larger import time overhead

## Suggestion
Remove `TYPE_CHECKING` from line 6:
