# TICKET-417

- Status: RESOLVED
- Class: (b) doc-drift (blanket docstring, no sub-component enumeration)
- File: personal_index/content_search.py
- Function: SnippetExtractor.extract (lines 52-89)

## Symptom
The `extract` docstring is a blanket over-promise:
"Finds the most relevant portions of text containing query terms and returns
them as highlighted snippets."
It does NOT enumerate the actual sub-components the body performs:
  1. Guard path: `if not text or not query_terms: return []` (empty text OR
     empty query list -> empty list, no snippet).
  2. No-match fallback: when no query term is found in the text, returns
     `self._make_fallback_snippet(text)` (a single Snippet of the leading
     portion of the text, ellipsis-suffixed if truncated) instead of [].
  3. Windowing: matched positions are grouped into windows by
     `_group_into_windows` and each window becomes a Snippet via
     `_make_snippet` (text/highlighted/start_offset/end_offset/matched_terms).
  4. Cap: the result is truncated to `self.max_snippets` (default 3).

## Evidence
- personal_index/content_search.py:57-61 (docstring)
- personal_index/content_search.py:62-63 (guard `return []`)
- personal_index/content_search.py:76-78 (no-match fallback)
- personal_index/content_search.py:88 (cap `snippets[: self.max_snippets]`)

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate the guard path
(empty text or empty query_terms -> []), the no-match fallback (single leading
portion Snippet), the windowed Snippet fields, and the max_snippets cap. Add
ONE pinning test asserting the RETURNED Snippet object fields (text,
highlighted, start_offset, end_offset, matched_terms) for the normal match
case AND the guard-path input (empty text -> []) so one test pins both the
main behavior and the guard path.

## Issue: #672
