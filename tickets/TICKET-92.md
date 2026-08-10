# TICKET-92: Type error — `serializer.py` assigns list to dict variable in `_dataclass_to_dict()`

## Title
`result[f.name]` assigned a list value but `result` was inferred as `dict[Any, Any]` from prior context

## Evidence
File: `personal_index/serializer.py`
Line 100: `result[f.name] = [...]` — assigns a list comprehension result

mypy flags: `personal_index/serializer.py:100: error: Incompatible types in assignment (expression has type "list[dict[Any, Any] | Any]", target has type "dict[Any, Any]")  [assignment]`

The issue is that `result` is initialized as `{}` on line 92, and mypy infers its type from the first assignment. When a nested dataclass field is encountered first, `result` gets typed as `dict[Any, Any]`, and subsequent list assignments conflict.

## Impact
Type checking fails. Runtime behavior is correct since Python dicts can hold mixed value types.

## Suggestion
Add explicit type annotation: `result: dict[str, Any] = {}` on line 92.
