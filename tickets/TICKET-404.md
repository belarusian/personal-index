# TICKET-404: importer.import_from_content docstring over-promise (class b)

- File: personal_index/importer.py
- Function: Importer.import_from_content (line 88)
- Symptom: docstring "Import bookmarks from content string with specified
  format." is a blanket adjective; it does not enumerate the fmt
  normalization, the dispatch table, or the unsupported-format return.
- Evidence: line 89 docstring; body lines 90-100 normalize
  `fmt = fmt.lower().lstrip(".")`, dispatch json/csv/html|necko|netscape/xml
  to the private helpers, and on no match return
  `ImportResult(errors=[f"Unsupported format: {fmt}"], source=source, format=fmt)`.
- Minimal additive fix: reword the docstring to the exact behavior (normalize,
  dispatch table, unsupported-format return) and add ONE pinning test that
  calls `import_from_content` directly with an unsupported fmt and asserts the
  RETURNED ImportResult fields (errors/source/format/total_imported).
- Status: RESOLVED (cycle 162, PR #647, merged 16e926c)
- Issue: #646
