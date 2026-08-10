# TICKET-93: Type error — `content_export_csv.py` `csv.QUOTE_ALL` (int) not matching Literal type

## Title
`csv.writer()` called with `quoting=csv.QUOTE_ALL` — mypy expects `Literal[0, 1, 2, 3, 4, 5]`

## Evidence
File: `personal_index/content_export_csv.py`
Line 152: `writer = csv.writer(f, quoting=csv.QUOTE_ALL, ...)`

mypy flags: `personal_index/content_export_csv.py:152: error: Argument "quoting" to "writer" has incompatible type "int"; expected "Literal[0, 1, 2, 3, 4, 5]"  [arg-type]`

`csv.QUOTE_ALL` is an `int` constant (value 1), but mypy's csv stubs expect a `Literal` type.

## Impact
False positive from mypy — runtime behavior is correct. Creates noise in type checking output.

## Suggestion
Add `# type: ignore[arg-type]` comment, or use the literal integer value directly: `quoting=1`.
