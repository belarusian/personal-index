# TICKET-435: content_priority.PriorityCalculator.get_summary docstring over-promise

- File: personal_index/content_priority.py
- Function: PriorityCalculator.get_summary
- Symptom (class-(b) doc-drift): docstring Returns says "Dict mapping priority
  level names to counts." which implies ALL five PriorityLevel values
  (critical/high/medium/low/archive) are always present as keys. The body
  (content_priority.py:236-240) only inserts a key for each level that is
  PRESENT in `results` (summary[level] = summary.get(level, 0) + 1); absent
  levels are omitted, and an empty `results` list returns {}.
- Evidence:
  - docstring (content_priority.py:226-233): "Returns: Dict mapping priority
    level names to counts."
  - body: `summary: dict[str, int] = {}` then `for result in results:
    level = result.priority.value; summary[level] = summary.get(level, 0) + 1`
    -> only present levels keyed; empty input -> {}.
- Minimal additive fix: reword the Returns clause to state the EXACT behavior:
  a dict mapping each PriorityLevel.value that is PRESENT in `results` to its
  count; levels with no matching result are omitted; an empty `results` list
  returns {}. Add ONE pinning test asserting the returned dict fields for the
  normal case (mixed levels -> only present keys, counts correct) AND the
  empty-results guard path (returns {}).
- Status: RESOLVED (90b0fc2)
- Issue: #708
