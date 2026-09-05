# TICKET-396: content_summarizer._word_frequency docstring over-promise

## File
`personal_index/content_summarizer.py`

## Symptom
The docstring `"""Calculate word frequency from text."""` (line 70) is a generic
single-line placeholder. It does not enumerate the actual sub-components:
(1) calls `_tokenize(text)` to get lowercase alphanumeric tokens,
(2) skips tokens in the module-level `STOPWORDS` frozenset,
(3) skips tokens with `len(word) <= 2`,
(4) accumulates counts via `freq.get(word, 0) + 1`,
(5) returns `dict[str, int]`.

## Evidence
Line 70: `"""Calculate word frequency from text."""`
Body (lines 71-77): calls `_tokenize`, iterates, checks `word not in STOPWORDS and len(word) > 2`, builds dict.

## Minimal additive fix
Reword docstring to enumerate the exact filtering conditions and return type.
Add one pinning test asserting that stopwords and short words are excluded
from the returned dict.

## Status
OPEN
Issue: #630
