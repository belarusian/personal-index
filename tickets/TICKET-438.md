# TICKET-438: ScoreWeights.normalize docstring over-promise (blanket statement)

- Status: OPEN
- Module: personal_index/content_scoring.py
- Function: ScoreWeights.normalize (line 48)

## Symptom
The docstring is a blanket statement:
    "Normalize weights so they sum to 1.0."
It does NOT enumerate:
  1. The guard path: when the sum of all six weights is 0, it returns the
     DEFAULT ScoreWeights() (recency=0.2, relevance=0.25, engagement=0.15,
     quality=0.15, authority=0.1, freshness=0.15) instead of dividing by zero.
  2. That it returns a NEW ScoreWeights instance (the original is not mutated).
  3. The exact division semantics: each of the six weights is divided by the
     total (sum of all six), so the returned weights sum to 1.0.

## Evidence
personal_index/content_scoring.py lines 48-62:
    def normalize(self) -> ScoreWeights:
        """Normalize weights so they sum to 1.0."""
        total = sum([...six weights...])
        if total == 0:
            return ScoreWeights()
        return ScoreWeights(recency=self.recency / total, ...)

## Minimal additive fix
Reword the docstring to state the EXACT conditional (guard path + return-new
instance + division semantics). Add ONE pinning test asserting the RETURNED
OBJECT fields:
  - normal case: custom weights -> each field == weight/total, sum ~1.0, and
    the ORIGINAL instance is unchanged (not mutated).
  - guard path: all-zero weights -> returned object equals the default
    ScoreWeights() fields (0.2/0.25/0.15/0.15/0.1/0.15), not a division error.

## Issue
Issue: #714
