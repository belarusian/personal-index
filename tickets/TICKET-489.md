# TICKET-489: ContentTransformer.transform docstring omits passthrough behavior

Status: RESOLVED (merged via PR #832)

## File
personal_index/content_transform/transformer.py

## Symptom
`ContentTransformer.transform` docstring (lines ~22-33) says only "Transform a
content item." It does not state the two distinct behaviors the code actually
delivers:
1. If `transform_fn` is set, it is called with `content` and its return value
   is returned.
2. If `transform_fn` is None, a shallow copy of the input dict (`dict(content)`)
   is returned unchanged (not the same object, same contents).

## Evidence
- Code: `if self.transform_fn: return self.transform_fn(content)` / `return dict(content)`.
- Live: `t=ContentTransformer(); d={'a':1}; r=t.transform(d); print(r is d, r==d)` -> `False True`.

## Minimal additive fix
- Reword the `transform` docstring to state both behaviors (transform_fn call;
  None passthrough as a shallow copy).
- Append `TestTransformerTransformPinning` to tests/test_content_transform.py
  covering: (a) transform_fn set -> fn called, result returned;
  (b) transform_fn None -> shallow copy returned (not same object, same contents);
  (c) input dict not mutated in either case.

Issue: #831
