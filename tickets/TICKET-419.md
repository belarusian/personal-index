# TICKET-419

- Status: OPEN
- Class: (b) doc-drift (blanket docstring, no sub-component enumeration)
- File: personal_index/content_scoring.py
- Function: ContentScorer.score (line 146)

## Symptom
The `score` docstring is a blanket over-promise:
"Calculate composite score for a content item."
It does NOT enumerate the actual sub-components the body performs:
  1. Computes six factor scores via dedicated helpers:
     recency=_score_recency(published_at, updated_at) (exponential decay,
     30-day half-life; naive datetimes made UTC-aware; date = updated_at or
     published_at or now),
     relevance=_score_relevance(keyword_matches, total_keywords) (0.0 when
     total_keywords==0, else min(1.0, matches/total)),
     engagement=_score_engagement(view_count, bookmark_count, share_count)
     (log1p weighted 0.4/0.4/0.2, capped at log1p(1000)),
     quality=_score_quality(word_count, has_images, has_code) (log1p length
     scaled to log1p(3000) + 0.1 image bonus + 0.05 code bonus, capped 1.0),
     authority=_score_authority(domain_authority, is_verified_source)
     (domain_authority + 0.1 only when verified, capped 1.0),
     freshness=_score_freshness(last_crawled, change_frequency, updated_at)
     (0.5 when last_crawled is None; 1.0 when frequency is "never"; else
     1.0 - 0.5*age_hours/expected, clamped to [0,1]).
  2. total = _compute_total(...) = weighted sum of the six factors using
     self.weights (normalized in __init__).
  3. Returns _build_score(...) -> ContentScore with total/recency/relevance/
     engagement/quality/authority/freshness each rounded to 4 places and a
     factors dict mapping each factor name to its unrounded value.

## Evidence
- personal_index/content_scoring.py:164 (blanket docstring)
- personal_index/content_scoring.py:165-172 (six _score_* calls + _compute_total + _build_score)
- personal_index/content_scoring.py:127-144 (_build_score rounds + factors dict)

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate the six factor
helpers and their guard conditions, the weighted total via normalized
self.weights, and the ContentScore fields (rounded to 4 places + factors
dict). Add ONE pinning test asserting the RETURNED ContentScore object fields
(total, recency, relevance, engagement, quality, authority, freshness, factors)
for a normal case AND the guard-path input (no-arg default call -> relevance
0.0, engagement 0.0, quality 0.0, authority 0.5, freshness 0.5, factors dict
populated) so one test pins both the main behavior and the guard path.

## Issue: #676
