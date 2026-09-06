# TICKET-465

## File
`personal_index/content_importer.py` — `ContentImporter.import_content` (line 24)

## Symptom
Class-(b) doc-drift: the docstring is the generic one-liner
`"""Import content from the given string data in the specified format."""`
which enumerates none of the behavior the body actually performs.

## Evidence (line)
- L25: `"""Import content from the given string data in the specified format."""`
- L26: `fmt = fmt.lower().strip()` (normalization not documented)
- L27-28: `if fmt not in self.SUPPORTED_FORMATS: raise ValueError(...)` (guard not documented)
- L29: `handler = getattr(self, f"_import_{fmt}")` (dispatch not documented)
- L30-31: `result = handler(data); return result` (return not documented)

## Minimal additive fix
Reword the `import_content` docstring to enumerate, in order:
(1) `fmt` is normalized via `lower().strip()`;
(2) a `ValueError` is raised when the normalized format is not in
`SUPPORTED_FORMATS` (json, html, markdown, rss, csv);
(3) dispatch to the private `_import_{fmt}` handler;
(4) return the handler's list of item dicts.
NO behavior change. Add pinning tests for the normalization + guard + dispatch.

Issue: #771

## Status
OPEN
