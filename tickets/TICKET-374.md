# TICKET-374

Status: RESOLVED (merged to main 4882571, gh #586 closed)
Issue: #586
Class: (a) behavioral

## File
personal_index/content.py — ExtractedContent.get_keywords() (lines 30-41)

## Symptom
get_keywords() extracts words from headings and meta keywords but never
filters stopwords, even though the same module defines STOPWORDS (line 41)
and remove_stopwords() (line 126). A heading like "Introduction to Python"
yields the stopword "to" as a keyword:

    >>> ExtractedContent(url='x', meta_keywords=[],
    ...     headings=['h1: Introduction to Python']).get_keywords()
    ['introduction', 'python', 'to']   # 'to' is a stopword

This is inconsistent with the module's own stopword vocabulary and with the
purpose of keyword extraction (keywords should be meaningful terms, not
function words).

## Evidence
- content.py:30-41 — get_keywords() builds `keywords` from meta_keywords +
  heading words, returns list(set(keywords)); no stopword filtering.
- content.py:41-56 — STOPWORDS set defined in the same module.
- content.py:126-135 — remove_stopwords() helper exists but is unused by
  get_keywords().
- Probe: `python3 -c` above returns 'to' in keywords.

## Minimal additive fix
In get_keywords(), filter the extracted heading words through remove_stopwords()
(the module's own helper) before returning. Meta keywords (author-supplied)
are kept as-is; only the auto-extracted heading words are stopword-filtered.
Add a behavior test pinning that a stopword in a heading is NOT returned as a
keyword while real words are.
