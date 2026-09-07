# Scoring (`personal_index.content_scoring`)

Status: **spec** — audited against current code (cycle 169).

`ScoreFactor` enum: RECENCY / RELEVANCE / ENGAGEMENT / QUALITY / AUTHORITY /
FRESHNESS.

## ScoreWeights
Six float weights (defaults: recency 0.2, relevance 0.25, engagement 0.15,
quality 0.15, authority 0.1, freshness 0.15).
- `normalize() -> ScoreWeights` — returns a NEW ScoreWeights whose six weights
  sum to 1.0 (each divided by the total). **Guard path:** when the total is 0
  (all six weights 0), returns the DEFAULT `ScoreWeights()` instead of
  dividing by zero. The original instance is not mutated.

## ContentScore
Fields: `total`, `recency`, `relevance`, `engagement`, `quality`, `authority`,
`freshness`, `factors` (dict). `to_dict()` rounds the seven floats to 4 places.

## ContentScorer
`ContentScorer(weights: ScoreWeights | None = None)` — uses `weights` or the
default `ScoreWeights()`.
- `score(...) -> ContentScore` — computes each of the six factor scores
  (`_score_recency`, `_score_relevance`, `_score_engagement`, `_score_quality`,
  `_score_authority`, `_score_freshness`), combines them via
  `_compute_total` (weighted sum using the normalized weights) into `total`,
  and builds the `ContentScore` via `_build_score`.
- `score_page(...) -> ContentScore` — a convenience wrapper over `score` that
  derives factor inputs from raw content/title/url (e.g. code detection via
  regex).
- `rank(...) -> list` — sorts items by score.

## Contract holes
- None found this cycle. `ScoreWeights.normalize` and `_compute_total` /
  `_build_score` docstrings were already reworded to exact-contract form in
  prior cycles (164, 167, 168).
