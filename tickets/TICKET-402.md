# TICKET-402: importer.import_from_file docstring over-promises "auto-detecting format"

- Status: OPEN
- File: personal_index/importer.py
- Function: `Importer.import_from_file` (line 50)
- Symptom: docstring `"""Import bookmarks from a file, auto-detecting format."""`
  is a blanket adjective. It does not enumerate the actual sub-components:
  the file-exists guard, the extension whitelist against SUPPORTED_FORMATS,
  the utf-8 read + delegation to import_from_content, or the exact
  ImportResult shapes returned on each early-exit path.
- Evidence: line 51 (docstring); body lines 52-67.
- Minimal additive fix: reword the docstring to enumerate the exact
  conditional / sub-components (file-not-found path, unsupported-extension
  path, delegation path, no direct _manager side effects), and add ONE
  pinning test in tests/test_importer.py asserting the returned
  ImportResult fields (errors message + source == filepath for the
  file-not-found path; format == ext for the unsupported path).
