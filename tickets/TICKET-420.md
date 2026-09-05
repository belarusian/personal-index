# TICKET-420

- Status: OPEN
- File: personal_index/content_priority.py
- Function: PriorityCalculator.calculate (line 90)
- Symptom: class-(b) doc-drift. Docstring is the blanket one-liner
  "Calculate priority for a content item." It does not enumerate the four
  sub-factors (recency / content_score / interest_match / engagement), the
  per-factor guard conditions, the weighted total via PriorityConfig weights,
  or the returned PriorityResult fields.
- Evidence: line 100 `"""Calculate priority for a content item."""`
- Minimal additive fix: reword the docstring to state the EXACT behavior
  (enumerate the four factors + their guard/threshold conditions, the weighted
  total using config weights, and the returned PriorityResult fields), and add
  ONE pinning test asserting the returned PriorityResult object fields for a
  normal case AND the no-arg guard path (recency=1.0, total=0.2 -> priority
  LOW, factors=["recently indexed"], breakdown populated with four keys).
- Issue: #678
