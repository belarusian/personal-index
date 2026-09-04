# TICKET-379: content_score not clamped to lower bound -> total score below 0.0

- Status: OPEN
- Issue: #596
- File: personal_index/content_priority.py
- Function: PriorityCalculator.calculate (line 107)
- Class: (a) behavioral

## Symptom
`calculate` normalizes the content score with
`score_n = min(content_score / 10.0, 1.0)`, which caps only the UPPER bound.
A negative `content_score` (e.g. -10.0) yields `score_n = -1.0`, a negative
factor. Because the four weights sum to 1.0, the weighted total can drop
below 0.0, violating the documented [0,1] invariant that the other three
factors (recency, interest, engagement) all enforce and that
`test_total_score_stays_in_0_1_range` explicitly pins ("weights sum to 1.0,
so every factor in [0,1] keeps the total in [0,1]").

## Evidence
Probe:
    PriorityCalculator().calculate(url='x', title='T', content_score=-10.0)
    -> breakdown['content_score'] == -1.0
    -> score == -0.09999999999999998  (below 0.0)
The other three factors are all clamped to [0,1]:
  _recency_score -> exp(-days/30) in (0,1]
  _interest_score -> min(len*0.25, 1.0) in [0,1]
  _engagement_score -> min(1.0, log(1+views)/log(101)) in [0,1]
Only score_n lacks the lower clamp.

## Minimal additive fix
Clamp score_n to the documented [0,1] range:
    score_n = min(max(content_score / 10.0, 0.0), 1.0)
This preserves existing behavior for content_score >= 0 (the upper cap is
unchanged) and fixes the negative case by flooring at 0.0. No change to the
other three factors or to the weights.

## Test
Add a behavior test that calls calculate with a negative content_score and
asserts breakdown['content_score'] >= 0.0 and 0.0 <= score <= 1.0. Fails
pre-fix (score == -0.0999...), passes post-fix.
