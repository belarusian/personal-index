# TICKET-457: ContentExporter.export docstring omits normalization + ValueError guard

- File: personal_index/content_exporter.py
- Symptom: class-(b) doc-drift. `ContentExporter.export` docstring is the blanket
  "Export a list of content items to the specified format." while the body (a)
  normalizes the format with `fmt = fmt.lower().strip()` (so "JSON " / " Html"
  are accepted, not just the exact lowercase token) and (b) raises
  `ValueError("Unsupported format: {fmt}. Supported: {SUPPORTED_FORMATS}")`
  when the normalized fmt is not in SUPPORTED_FORMATS ("html","json","markdown",
  "rss") before dispatching to the `_export_<fmt>` handler.
- Evidence: export body (lines ~24-31): `fmt = fmt.lower().strip()`;
  `if fmt not in self.SUPPORTED_FORMATS: raise ValueError(...)`.
- Minimal additive fix: reword the docstring to state the exact normalization
  (lower + strip) and the ValueError guard for unsupported formats; add ONE
  behavior test pinning the corrected claim against the returned object,
  including the guard-path (unsupported format -> ValueError) input alongside
  the normal case (a padded/upper-case format that normalizes and succeeds).
- Issue: #755

- Status: OPEN
- Note: renumbered 456 -> 457 at merge (parallel run claimed 456 for
  content_collections.CollectionManager.delete, PR #754).
