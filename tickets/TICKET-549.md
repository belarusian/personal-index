# TICKET-549: Add ContentScorer._compute_total exact-contract docstring + pinning test

Status: OPEN
Module: personal_index/content_scoring.py
Methods: ContentScorer._compute_total
Type: (b) private method lacking an exact-contract docstring + pinning test

## Symptom
`_compute_total` (line 125) has NO docstring. It is the weighted-sum core of the
scorer, so its contract is undocumented: which six factors it combines, that each
is multiplied by the corresponding `self.weights` field, and that the result is
the raw (unrounded) float sum of the six products.

## Evidence (verified live)
Lines 125-136:
    def _compute_total(
        self, recency: float, relevance: float, engagement: float,
        quality: float, authority: float, freshness: float,
    ) -> float:
        return (
            self.weights.recency * recency
            + self.weights.relevance * relevance
            + self.weights.engagement * engagement
            + self.weights.quality * quality
            + self.weights.authority * authority
            + self.weights.freshness * freshness
        )
No docstring present. `self.weights` is a normalized `ScoreWeights` (see
`__init__`, line 122: `self.weights = (weights or ScoreWeights()).normalize()`),
so the six weights sum to 1.0.

## Minimal additive fix
1. Add a docstring to `_compute_total` stating the exact contract: it returns the
   raw float sum of the six weighted products (weights.recency*recency +
   weights.relevance*relevance + weights.engagement*engagement +
   weights.quality*quality + weights.authority*authority +
   weights.freshness*freshness), using the normalized `self.weights`, and does NOT
   round or clamp the result (rounding happens later in `_build_score`).
2. Add ONE pinning test in tests/test_content_scoring.py that calls
   `_compute_total` with known factor values and asserts the returned float equals
   the hand-computed weighted sum against the returned object (normal case), plus
   the guard path: all-zero factors return 0.0.

Issue: #975
