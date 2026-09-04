# TICKET-346: content_scoring._score_authority docstring over-promises (class b)

Status: OPEN
Module: personal_index/content_scoring.py
Method: ContentScorer._score_authority (line 236)

## Symptom
The docstring reads only "Score based on source authority." — a blanket
adjective that does not state the exact conditional the body performs. The
body does: `score = domain_authority`; if `is_verified_source` then
`score = min(1.0, score + 0.1)`; then `round(score, 4)`. So the verified
source adds a +0.1 bonus that is capped at 1.0, and an unverified source
returns `domain_authority` unchanged. The docstring claims none of this.

## Evidence
- Line 237: `"""Score based on source authority."""`
- Lines 239-242:
    score = domain_authority
    if is_verified_source:
        score = min(1.0, score + 0.1)
    return round(score, 4)
- Verified 0.9 -> 1.0 (capped); unverified 0.9 -> 0.9.

## Minimal additive fix (doc-only, no behavior change)
Reword the docstring to state the exact conditional: the score equals
`domain_authority`, plus a +0.1 bonus only when `is_verified_source` is true,
capped at 1.0, rounded to 4 places. Add ONE behavior test pinning the
corrected claim against the returned object: verified 0.9 -> 1.0 (capped) and
unverified 0.9 -> 0.9 (unchanged).

## Issue: #530
