# TICKET-491: create_field_rename_transformer docstring drift

Status: RESOLVED (merged via PR #837)
File: personal_index/content_transform/transformer.py
Function: create_field_rename_transformer

## Symptom
Docstring says "Create a transformer that renames a field" without specifying the
actual contract: (1) returns a NEW dict (shallow copy), input never mutated;
(2) if old_name is absent, content is returned unchanged (no-op, no error);
(3) rename is a MOVE (pop old_name, set new_name); (4) name is
rename_{old_name}_to_{new_name}.

## Evidence
- Line: `result = dict(content)` — new dict, input not mutated
- Line: `if old_name in result:` — guard means absent old_name is a no-op
- Line: `result[new_name] = result.pop(old_name)` — move, not copy
- Line: `name=f"rename_{old_name}_to_{new_name}"` — name format

## Fix
Reword docstring to state the four behaviors. Add TestCreateFieldRenameTransformerPinning
with pinning tests locking: (a) rename when old_name present; (b) no-op when old_name
absent; (c) input not mutated + result is not input; (d) name format.

Issue: #836
