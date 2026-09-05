# TICKET-400

- Status: OPEN
- File: personal_index/importer.py
- Function: `_import_html` (line 166, docstring line 167)
- Symptom: docstring `"""Import from HTML bookmark format (Netscape/Neko)."""`
  is a generic single-line placeholder that does not enumerate the actual
  sub-components / behavior the body performs.
- Evidence: line 167 `"""Import from HTML bookmark format (Netscape/Neko)."""`;
  body first validates `content.strip()` starts with "<" and contains ">", else
  appends "Invalid HTML: content does not appear to be HTML" to
  `result.errors` and returns early; tries `BeautifulSoup(content, "html.parser")`
  (on `ImportError` falls back to `ET_fromstring` + `_parse_html_element`,
  appending "Invalid HTML/XML: ..." on `ET_ParseError`); with BeautifulSoup it
  iterates `soup.find_all("a", href=True)`, building a `Bookmark` from
  `href` (url), `title` attribute or `get_text(strip=True)` (title), and
  `category="imported"`; adds each to `self._manager` and increments
  `result.total_imported`; returns `ImportResult(format="html")`.
- Minimal additive fix: reword the docstring to enumerate the exact behavior
  (HTML-shape validation + early-return error, BeautifulSoup parse with
  ElementTree fallback, per-`<a href>` field extraction + category default,
  import accounting, returned `ImportResult`); add ONE pinning test in
  `tests/test_importer.py` (an `<a href>` with a `title` attribute -> assert
  `total_imported`, `format`, and the parsed title/category against the
  manager's stored bookmark).
- Line-shift guard: `tests/test_exception_handling.py` references `_import_html`
  only via `_method_line_span` (dynamic AST resolution by name), not hardcoded
  line ranges; `tests/test_importer.py` has no line-number references. Adding
  docstring lines is safe.
- Issue: #638
