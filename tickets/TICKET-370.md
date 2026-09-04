# TICKET-370: tokenize() silently drops single-letter words when remove_stopwords=False

**Status:** OPEN
**Issue:** #578
**Module:** personal_index/text_utils.py
**Defect class:** (a) behavioral

## Symptom
`tokenize("I am here", remove_stopwords=False)` returns `['am', 'here']` —
the single-letter word "I" is silently dropped. Same for "A", "I", etc.
The regex `\b[a-zA-Z][a-zA-Z0-9_-]+\b` requires a minimum of 2 characters
(letter + one-or-more), so any single-letter token never matches.

## Evidence