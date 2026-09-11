# ARCH-25: importer — total_skipped accounting is inconsistent across formats (HTML/OPML silently drop empty-url items)

- **Status:** CLAIMED 2026-09-10
- **Component:** `personal_index/importer.py` (`Importer`).
- **Issue:** #1068

## Symptom
`ImportResult.total_skipped` is documented as "count of items with an empty
`url` that were counted as skipped", but only **JSON, CSV, and XML** actually
increment it. The **HTML** path (both the BeautifulSoup branch and the
`_parse_html_element` fallback) and the **OPML** path **silently drop**
empty-`url` items — no `total_skipped` increment and no `errors` entry.

- `_import_json` / `_import_csv` / `_import_xml`: empty `url` →
  `result.total_skipped += 1`.
- `_import_html` (BeautifulSoup): `find_all("a", href=True)` never matches an
  `<a>` with no `href`, so such anchors are simply absent from the iteration —
  never counted.
- `_parse_html_element` (fallback): `if href:` guards the write; an `<a>` with
  no `href` falls through with no counter and no error.
- `import_opml`: `if url:` guards the write; a falsy `url` outline is skipped
  with no counter and no error.

A consumer that assumes the invariant
`total_imported + total_skipped == total_items_seen` gets correct accounting
for JSON/CSV/XML but **under-counts** for HTML/OPML: items that were seen and
deliberately not imported vanish from both counters.

## Evidence
- `personal_index/importer.py:152` — `_import_json`: `else: result.total_skipped += 1`.
- `personal_index/importer.py:189` — `_import_csv`: `else: result.total_skipped += 1`.
- `personal_index/importer.py:319` — `_import_xml`: `else: result.total_skipped += 1`.
- `personal_index/importer.py:231` — `_import_html` (BeautifulSoup): iterates
  `soup.find_all("a", href=True)`; no `href` → anchor not matched, no counter.
- `personal_index/importer.py:266` — `_parse_html_element`: `if href:` guards
  the write; no `else` branch.
- `personal_index/importer.py:349` — `import_opml`: `if url:` guards the write;
  no `else` branch.
- `personal_index/importer.py:26` — `ImportResult.total_skipped` default `0`,
  documented as the empty-url skip counter.

## Public contract (target state)
- Every format handler MUST account for every item it sees: an item with an
  empty/absent `url` MUST increment `result.total_skipped` (and NOT be written
  to the manager), matching the JSON/CSV/XML behavior.
- Concretely:
  - `_import_html` (BeautifulSoup): iterate anchors that may lack `href`
    (e.g. `find_all("a")`) and, when `href` is falsy, increment
    `total_skipped` instead of silently ignoring the anchor.
  - `_parse_html_element`: add an `else` branch to the `if href:` guard that
    increments `result.total_skipped` for an `<a>` with no `href`.
  - `import_opml`: add an `else` branch to the `if url:` guard that increments
    `result.total_skipped` for an outline with a falsy `url`.
- Behavior that MUST be preserved: no empty-`url` item is ever written to the
  manager; `total_imported` semantics are unchanged; the per-format
  title/description/category extraction is unchanged; the malformed-input
  guard paths (invalid JSON/HTML/XML/OPML) are unchanged.

## Acceptance criteria
1. For each of json/csv/html/xml/opml, an input containing one valid
   (non-empty-url) item and one empty-url item yields
   `total_imported == 1` and `total_skipped == 1`.
2. `import_from_content("<a href='http://x'>X</a><a>NoHref</a>", "html")`
   returns `total_imported == 1` and `total_skipped == 1` (previously
   `total_skipped == 0`).
3. `import_opml` on an OPML with one `xmlUrl` outline and one text-only
   (no `xmlUrl`/`htmlUrl`) outline returns `total_imported == 1` and
   `total_skipped == 1` (previously `total_skipped == 0`).
4. Existing `tests/test_importer.py` happy-path and guard-path assertions stay
   green (no empty-url item is written to the manager; `total_imported`
   values unchanged).

## Pinning tests to add
- `test_html_empty_href_increments_skipped` (guard path: an `<a>` with no
  `href` alongside a normal `<a href=...>`) — assert
  `total_imported == 1` and `total_skipped == 1`.
- `test_opml_falsy_url_increments_skipped` (guard path: a text-only outline
  with no `xmlUrl`/`htmlUrl` alongside a normal `xmlUrl` outline) — assert
  `total_imported == 1` and `total_skipped == 1`.
- `test_all_formats_account_seen_items` — for each of json/csv/html/xml/opml,
  feed one valid + one empty-url item and assert
  `total_imported + total_skipped == 2` (the invariant the hole breaks).

## Docs
`docs/importer.md` (this cycle) documents the hole; the implementer keeps the
page true when fixing (mark contract hole 1 RESOLVED and update the
per-format `total_skipped` lines to state that every format now accounts for
empty-url items).
