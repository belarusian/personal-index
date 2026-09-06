# TICKET-490: create_field_add_transformer docstring omits overwrite behavior

Status: RESOLVED (merged via PR #835)

## File
personal_index/content_transform/transformer.py

## Symptom
`create_field_add_transformer` docstring (lines ~101-111) says only "Create a
transformer that adds a field." It does not state the actual contract the code
delivers:
1. The transform returns a NEW dict (a shallow copy `dict(content)`), never the
   input object; the input dict is not mutated.
2. `result[field_name] = value` (line 116) SETS the field, so if `field_name`
   already exists in the content it is OVERWRITTEN with `value` — it is not
   merely "added".
3. The returned ContentTransformer is named `add_{field_name}` (line 120).

## Evidence
- Code: `result = dict(content)` / `result[field_name] = value` / `return result`.
- Live: `create_field_add_transformer('id','OVERRIDDEN').transform({'id':'1','tags':['a']})`
  -> `{'id': 'OVERRIDDEN', 'tags': ['a']}` (existing field overwritten).
- Live: input dict unchanged after transform.
- Live: transformer name -> `add_new_field`.

## Minimal additive fix
- Reword the `create_field_add_transformer` docstring to state the three
  behaviors (new-dict return / input not mutated; field set-or-overwritten;
  name `add_{field_name}`).
- Append `TestCreateFieldAddTransformerPinning` to tests/test_content_transform.py
  covering: (a) field absent -> set; (b) field present -> overwritten;
  (c) input not mutated; (d) returned name is `add_{field_name}`.

Issue: #834
