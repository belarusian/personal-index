# TICKET-283: search_suggestions trending suggestions drop every mixed-case query

- Status: OPEN
- Issue: #392
- Module: personal_index/search_suggestions.py
- Class: logic (case-sensitive prefix match against a lowercased prefix)

## Symptom
`SearchSuggestions._suggest_from_trending` (line 299) matches trending entries with
`if query.startswith(prefix)` (line 304) where `query = entry.query` is the ORIGINAL-CASE
query and `prefix` is the already-lowercased `prefix_lower` passed by `suggest()` (line 183).
Every other source method lowercases before matching:
- `_suggest_from_history`: `if query.lower().startswith(prefix)` (line 205)
- `_suggest_from_tags`: `if tag.lower().startswith(prefix)` (line 239)
- `_suggest_from_keywords`: `if kw.lower().startswith(prefix)` (line 272)

So a trending query recorded with mixed case (e.g. "Python") is silently dropped for any
lowercase prefix ("py", "python") because "Python".startswith("py") is False.

## Evidence
- personal_index/search_suggestions.py:304  `if query.startswith(prefix):`   <- original-case query vs lowercased prefix
- personal_index/search_suggestions.py:205  `if query.lower().startswith(prefix):`  (history, correct)
- personal_index/search_suggestions.py:239  `if tag.lower().startswith(prefix):`    (tags, correct)
- personal_index/search_suggestions.py:272  `if kw.lower().startswith(prefix):`     (keywords, correct)
- Runtime: record_search('Python')x2 + record_search('python'); suggest('py', sources=['trending']) -> []
           suggest('python', sources=['trending']) -> []  (all mixed-case trending queries dropped)

## Minimal additive fix
- In `_suggest_from_trending`, match on the lowercased query: `if query.lower().startswith(prefix):`
  (line 304). Keep `query` (original case) as the candidate key/text, matching the other
  source methods which key candidates by the original-case string.

## Regression tests (tests/test_search_suggestions.py)
- mixed-case trending query is returned for a lowercase prefix.
- lowercase trending query still returned (no regression).
