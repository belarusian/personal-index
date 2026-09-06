# TICKET-498: CategorizationResult.top_n docstring omits its exact contract

## File
personal_index/content_categorizer.py

## Function
CategorizationResult.top_n (line ~226)

## Symptom
The docstring reads only `"""Return top N topics."""` — a generic claim that
omits the actual observable contract:
- default `n` is 3
- returns a NEW list (a slice), not the internal `self.topics` list
- preserves the existing order of `self.topics` (score-descending as produced
  by the categorizer)
- `n=0` returns an empty list; `n` larger than `len(topics)` returns all topics
- does not mutate `self.topics`

## Evidence (verified live)
- top_n() -> [a(0.9), b(0.5), c(0.1)]   (default n=3)
- top_n() is not r.topics -> True        (new list, not the internal list)
- top_n(10) -> [a, b, c]                 (n > len returns all)
- top_n(0) -> []                         (empty)

## Minimal additive fix
Reword the `top_n` docstring to state the exact contract above, and append
pinning tests to tests/test_content_categorizer.py pinning: default n=3,
new-list (not the internal list), n=0 -> [], n > len -> all, no mutation.

## Status
RESOLVED (merged via PR #853)

Issue: #852
