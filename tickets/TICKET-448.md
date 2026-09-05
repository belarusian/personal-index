# TICKET-448: content_filter.get_filter_reasons check 8 scores content-only, not the documented title+content

Status: OPEN
Issue: #735
Module: personal_index/content_filter.py
Method: ContentFilter.get_filter_reasons (check 8, minimum relevance score)

## Symptom
The `get_filter_reasons` docstring (check 8) claims: "an interest_store
exists, config.min_relevance_score > 0, and the store total_score for
**title+content** is below that minimum". But the body computes
`score = self.interest_store.total_score(page.content)` — content ONLY,
the title is excluded. This is also internally inconsistent with the
sibling check 7 `_matches_interests`, which scores
`total_score(text)` where `text = f"{page.title} {page.content}"`
(title+content). The code does not deliver the documented title+content
scoring.

## Evidence
personal_index/content_filter.py:
- docstring line 71: "store total_score for title+content is below that minimum"
- body line 104: `score = self.interest_store.total_score(page.content)`
- sibling check 7, line 148: `page.relevance_score = self.interest_store.total_score(text)`
  where `text = f"{page.title} {page.content}"` (line 147)

## Classification
IMPLEMENTABLE. `total_score(text)` accepts any text; scoring the combined
title+content string is a one-line change that makes the ORIGINAL claim
true and aligns check 8 with check 7.

## Minimal additive fix
In `get_filter_reasons` check 8, score the combined title+content text
(the same `f"{page.title} {page.content}"` form check 7 uses) instead of
`page.content`. Add ONE pinning test: a page whose title contains the
keyword but whose content does not, with min_relevance_score set so the
title-only occurrence pushes the score over the minimum — assert the
page is INCLUDED (score counted title+content) and that the reason list
has no "relevance score" entry. This pins the title+content claim.
No other behavior change.
