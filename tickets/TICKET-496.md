# TICKET-496: pipeline.py transform/transform_batch docstring reword + pinning tests

Status: RESOLVED

## File
personal_index/content_transform/pipeline.py

## Symptom
TransformPipeline.transform (lines ~35-43) and TransformPipeline.transform_batch
(lines ~49-60) carry generic docstrings ("Apply all transformers in sequence." /
"Apply pipeline to multiple items.") that omit the actual contract.

## Evidence (verified live)
- transform: returns a NEW dict (dict(content) copy) — input never mutated,
  result is not the input object; transformers applied in add() order; an empty
  pipeline returns a copy equal to (but not identical to) the input.
- transform_batch: returns a NEW list (list comprehension) — input list never
  mutated, result is not the input object; each item transformed via
  self.transform, order preserved, each output item a new dict; empty input ->
  empty list (no error).

## Minimal additive fix
Reword both docstrings to state the exact contract; append pinning tests to
tests/test_content_transform.py (annotate list literals as list[dict[str, Any]]
to dodge mypy list[object] inference).

Issue: #846
