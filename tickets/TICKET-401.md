# TICKET-401: import_opml docstring is a generic placeholder

- **File**: `personal_index/importer.py`
- **Symptom**: `import_opml` docstring (line 284) is `"""Import from OPML format."""` — a single-line placeholder that does not enumerate the actual sub-components/behavior.
- **Evidence**: Line 284: `"""Import from OPML format."""`
- **Minimal additive fix**: Reword docstring to enumerate: ET_fromstring parse + ET_ParseError early-return with "Invalid OPML: {e}"; iterates `.//outline[@text]`; xmlUrl-over-htmlUrl precedence; title-attr-over-text-attr precedence; Bookmark(url, title, category="imported") added to self._manager when url truthy; no total_skipped increment when url falsy; returns ImportResult(format="opml"). Add one pinning test asserting against the manager's stored bookmark (title-attr precedence + category default).
- **Status**: OPEN
- **Issue**: #640
