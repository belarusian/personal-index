# TICKET-430

**Module:** personal_index/content_scoring.py
**Function:** ContentScorer.score_page
**Class:** (b) doc-drift — blanket docstring that does not enumerate sub-components
**Status:** RESOLVED
**Issue:** #698

## Symptom
`score_page`'s docstring is a single blanket line:
    """Score a CrawledPage using interest matching."""
It does not enumerate the sub-components the body actually performs: the
content/word_count extraction from the page, the interest-matching loop that
only runs when `interest_store` is truthy, the has_code/has_images regex
detection, the delegation to `self.score(...)`, and the guard path (falsy
`interest_store` -> zero keyword matches).

## Evidence
- personal_index/content_scoring.py:317  (the one-line docstring)
- Body lines 318-345: content/word_count extraction, `if interest_store:`
  loop over `interest_store.list_all()` counting keywords/topics/value,
  has_code/has_images regex, `self.score(...)` with
  `total_keywords=max(total_keywords, 1)`.

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate the fields read
from the page, the interest-matching loop (and that it is skipped when
`interest_store` is falsy), the has_code/has_images regex detection, the
delegation to `self.score(...)` (with the `total_keywords` floor of 1 and the
`domain_authority`/`last_crawled` defaults), and the guard path (falsy
`interest_store` -> keyword_matches=0, total_keywords floored to 1 ->
relevance 0.0). Add ONE pinning test asserting the returned ContentScore
fields for the normal case (interest_store with a matching keyword ->
relevance > 0) AND the guard path (no interest_store -> relevance 0.0).
No behavior change.
