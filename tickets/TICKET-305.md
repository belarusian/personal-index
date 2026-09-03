# TICKET-305: content_priority.py PriorityCalculator._engagement_score exceeds documented 0-1 range

- Status: OPEN
- Module: personal_index/content_priority.py
- Class: (b) doc/behavior drift — documented return range not honored by the body
- Site: personal_index/content_priority.py:145-153 - `def _engagement_score(self, view_count: int) -> float:`

## Symptom
`_engagement_score` documents "Calculate engagement score (0-1)" (line 146) and
"Uses logarithmic scaling: score = log(1 + views) / log(101)" (line 148). The body
(line 153) returns `math.log(1 + view_count) / math.log(101)` with **no cap**. For
`view_count > 100` the value exceeds 1.0, violating the documented 0-1 range.

## Evidence (verified at runtime)
- `view_count=100` -> `1.0000` (in range)
- `view_count=101` -> `1.0021` (OUT of range)
- `view_count=1000` -> `1.4970` (OUT of range)
- `view_count=10000` -> `1.9957` (OUT of range)

The denominator `log(101) = log(1 + 100)` is a deliberate normalization: the formula
reaches **exactly 1.0 at view_count = 100**, i.e. the author intended the score to
saturate at 1.0 for 100+ views but omitted the cap.

## Why the body is the true drift (not the docstring)
1. The formula's own normalization point (1.0 at 100 views) shows 1.0 is the
   intended ceiling; the missing `min(..., 1.0)` is the defect.
2. The sibling `_interest_score` (line 135-140) explicitly caps with
   `min(len(matches) * 0.25, 1.0)` — the module's own "score (0-1)" convention.
3. The parallel `content_scoring.py::_score_engagement` caps at 1.0
   (`min(1.0, engagement / max_engagement)`).
4. Class invariant: the four factor weights sum to 1.0 (0.2+0.3+0.3+0.2), so if every
   factor is in [0,1] the weighted total is in [0,1]. `from_score` documents "a
   normalized score (0-1)" and the level thresholds (0.8/0.6/0.4/0.2) are designed for
   that range. Uncapped engagement breaks the invariant:
   `calculate(view_count=10000, ...)` -> total `1.1991` (breakdown engagement `1.9957`).

## Minimal additive fix
Cap the return at 1.0 to match the documented 0-1 range and the module's own
convention:
    return min(1.0, math.log(1 + view_count) / math.log(101))

## Regression test
Add a test asserting `_engagement_score` stays within [0.0, 1.0] across a range of
view counts (0, 1, 10, 100, 101, 1000, 10000) and that it is non-decreasing, and that
a high-view item's total score stays within [0,1].

## Issue: #443
