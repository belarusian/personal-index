# TICKET-494: transform_batch docstring does not state the exact contract

Status: RESOLVED
Module: personal_index/content_transform/transformer.py
Method: ContentTransformer.transform_batch (lines ~41-52)

## Symptom
The docstring says only "Transform multiple content items." with generic
Args/Returns. It does not state the actual contract the code delivers:
(1) returns a NEW list (list comprehension) — the input list is never mutated
and the result is not the input object; (2) each item is transformed via
self.transform(item), order preserved; (3) empty input list -> empty list
(no error).

## Evidence (verified live)
- input unchanged after transform_batch: True
- result is not input: True
- order preserved + each item transformed: True
- empty -> empty list: True
- each output item is a new dict (not the input item object): True

## Minimal additive fix
1. Reword the transform_batch docstring to state the three behaviors above.
2. Append a pinning test class TestTransformBatchPinning to
   tests/test_content_transform.py (construct a concrete transformer via
   create_field_add_transformer; pin new-list/not-mutated, order preserved,
   empty -> empty).

Issue: #840

Resolved: 2026-09-06, merged via PR #842 (issue #840 closed).
