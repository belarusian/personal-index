# TICKET-380: _find_match_indices returns [] when query is longer than text -> match cannot be highlighted

- Status: OPEN
- Issue: #598
- File: personal_index/fuzzy_search.py
- Function: FuzzySearcher._find_match_indices (line 178)
- Class: (a) behavioral

## Symptom
`search` returns a `FuzzyMatch` with a non-trivial score but an EMPTY
`matched_indices` list whenever the query is longer than the candidate text
(e.g. `search("hello world", ["hello"])` -> score 0.7, matched_indices []).
Because `highlight` / `highlight_html` / `search_with_highlight` build the
highlighted output purely from `matched_indices`, these returned matches are
never highlighted, while every other match (query <= text) is. The module is
internally inconsistent: a match that is returned but cannot be highlighted.

## Evidence
Probe:
    FuzzySearcher().search("hello world", ["hello"])
    -> [FuzzyMatch(text="hello", score=0.7, matched_indices=[])]
    -> search_with_highlight("hello world", ["hello"])[0][1] == "hello"
       (no "\033[1m" marker, no "<mark>")
Contrast (query <= text, works):
    FuzzySearcher().search("hello", ["say hello there"])
    -> matched_indices == [4,5,6,7,8], highlight has marker.
Root cause: in the `else` branch of `_find_match_indices`, the best-substring
loop is `for i in range(len(text) - len(query) + 1)`. When `len(query) >
len(text)` that range is empty, so the loop body never runs and `indices`
stays `[]` regardless of how well the text matches the query.

## Minimal additive fix
In the `else` branch, handle the `len(query) > len(text)` case: find the best
window of `query` (of length `len(text)`) that matches `text` using
SequenceMatcher, and if its ratio > 0.5 (same threshold as the existing
substring case), return the whole text as the matching region
(`list(range(len(text)))`). The existing `len(query) <= len(text)` path is
left byte-for-byte unchanged, so this is purely additive: it only fills in
indices for the previously-empty case and cannot alter any existing result.

## Test
Add a behavior test: `search("hello world", ["hello"])` returns a match whose
`matched_indices == [0,1,2,3,4]` and whose `search_with_highlight` output
contains the highlight marker. Fails pre-fix (indices == [], no marker),
passes post-fix.
