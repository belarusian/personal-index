# TICKET-399

- Status: OPEN
- File: personal_index/importer.py
- Function: `_import_xml` (line 220, docstring line 221)
- Symptom: docstring `"""Import from generic XML format."""` is a generic
  single-line placeholder that does not enumerate the actual sub-components /
  behavior the body performs.
- Evidence: line 221 `"""Import from generic XML format."""`; body parses
  `content` via `ET_fromstring`, on `ET_ParseError` appends "Invalid XML: ..."
  to `result.errors` and returns early; iterates `root.findall(".//bookmark")`,
  building a `Bookmark` from url/title/description/category (default
  "imported")/tags (comma-split, stripped); adds to `self._manager` and
  increments `result.total_imported` when `bookmark.url` is truthy, else
  `result.total_skipped`; per-element `ValueError`/`TypeError` are caught and
  appended to `result.errors`; returns `ImportResult(format="xml")`.
- Minimal additive fix: reword the docstring to enumerate the exact behavior
  (parse-or-error early return, per-bookmark field extraction + defaults,
  comma-split tags, url-truthy import-vs-skip accounting, per-element error
  capture, returned `ImportResult`); add ONE pinning test in
  `tests/test_importer.py` (a bookmark with comma-separated `tags` and one
  bookmark with an empty url -> assert `total_imported`/`total_skipped` and the
  parsed tags list).
- Line-shift guard: `tests/test_exception_handling.py` references `_import_xml`
  only via `_method_line_span` (dynamic AST resolution by name), not hardcoded
  line ranges; `tests/test_importer.py` has no line-number references. Adding
  docstring lines is safe.
- Issue: #636
