# TICKET-493: create_field_filter_transformer docstring drift

Status: OPEN
File: personal_index/content_transform/transformer.py
Function: create_field_filter_transformer

## Symptom
Docstring says "Create a transformer that filters to specific fields" without
specifying the actual contract: (1) returns a NEW dict (dict comprehension),
input never mutated; (2) keeps only keys present in `fields` (order of the
input is preserved); (3) if no key matches (or `fields` is empty), returns an
empty dict (no error); (4) name is filter_fields_{len(fields)}.

## Evidence
- Line: `return {k: v for k, v in content.items() if k in fields}` — new dict,
  input not mutated; only matching keys kept; empty when no match
- Line: `name=f"filter_fields_{len(fields)}"` — name format (count-based)

## Fix
Reword docstring to state the four behaviors. Add TestCreateFieldFilterTransformerPinning
with pinning tests locking: (a) keeps only listed fields; (b) empty dict when no
match / empty fields; (c) input not mutated + result is not input; (d) name format.

Issue: #838
