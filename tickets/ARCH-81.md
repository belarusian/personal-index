# ARCH-81: _export_html emits unbalanced <DL> tags (malformed Netscape HTML)

Status: CLOSED (validator cycle 256 @ main cde594c: pinning tests + adversarial input green) #1539@bf254f9 (cycle 309)
Component: personal_index.export (personal_index/export.py)
Issue: #1438

## Symptom

`Exporter._export_html` (line 121) produces Netscape HTML with an unbalanced
`<DL>`/`</DL>` pair. It opens exactly one list container with the literal
`'<DL><p>'` (line 128) but closes it with
`lines.extend(["</DL><p>", "</DL>"])` (line 136) — that is **two** `</DL>`
closing tags for **one** opening `<DL>`. The emitted document therefore has one
extra `</DL>` with no matching open tag, so the Netscape bookmark file is
structurally malformed: a strict HTML parser (or a browser's DOM) sees an
unbalanced container.

## Evidence

- `personal_index/export.py:128` — `'<DL><p>'` (one opening `<DL>`).
- `personal_index/export.py:136` — `lines.extend(["</DL><p>", "</DL>"])`
  (two closing `</DL>`).
- `tests/test_export.py` — `test_export_html_content` (line 99),
  `test_export_html_escapes_special_chars` (line 105), and
  `test_export_html_file` (line 112) assert only substrings (the DOCTYPE, an
  `HREF`, and escape entities). None pin `<DL>`/`</DL>` balance, so the defect
  is unpinned.

## Failing input / observed vs expected

- Input: any `BookmarkManager` (even empty) rendered via
  `Exporter(manager).export_to_content("html")`.
- Observed: the output contains one `<DL>` and two `</DL>` (count of `"<DL>"`
  == 1, count of `"</DL>"` == 2).
- Expected: balanced containers — one `<DL>` and exactly one `</DL>` (the
  Netscape format is a single `<DL>` wrapping the `<DT>/<DD>` items, closed
  once).

## Contract (what the fix must do)

1. `_export_html` must emit **balanced** `<DL>`/`</DL>` tags: exactly one
   opening `<DL>` and exactly one closing `</DL>` for the bookmark list.
2. The DOCTYPE, `<META>`, `<TITLE>`, `<H1>`, and per-bookmark `<DT><A ...>`
   lines must be unchanged.
3. All other formats (`json`, `csv`, `xml`, `markdown`, `opml`) must be
   byte-for-byte unchanged.
4. The graceful-degradation behavior for unsupported formats (no raise) must be
   unchanged.

## Acceptance Criteria

- [ ] `Exporter(manager).export_to_content("html")` output has
      `content.count("<DL>") == 1` and `content.count("</DL>") == 1`.
- [ ] The output still contains the DOCTYPE, an `HREF` for each bookmark, and
      the escaped entities (existing HTML tests still pass unchanged).
- [ ] `json`/`csv`/`xml`/`markdown`/`opml` outputs are unchanged (their existing
      tests still pass unchanged).
- [ ] `docs/export.md` "Documented Contract Hole" section is updated to reflect
      the corrected (balanced) HTML contract.

## Pinning Tests to Add

In `tests/test_export.py` (HTML class):
- CLOSED (architect, cycle 311): contract VERIFIED by the validator (PR #1539); docs reconciled; closing the VERIFIED pile.
