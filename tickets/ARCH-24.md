# ARCH-24: content_importer — item shape is inconsistent across formats (only JSON is normalized)

- **Status:** OPEN
- **Component:** `personal_index/content_importer.py` (`ContentImporter`).
- **Issue:** #1065

## Symptom
`ContentImporter.import_content(data, fmt)` promises a uniform list of item
dicts, but only the **JSON** path routes through `_normalize_items`, so only
JSON items are guaranteed the `title/description/link/id/tags/date` key set.
Every other format emits its own ad-hoc key set:

- `_import_html` fallback (no `<article>` found) emits `title/description/id`
  and **omits `link` entirely**.
- `_import_markdown` emits `title/link/id` (+ `description` at flush) — no
  `tags`, no `date`.
- `_import_rss` emits `title/description/link/id` — no `tags`, no `date`.
- `_import_csv` emits only the non-empty CSV header columns (+ minted `id`) —
  shape depends entirely on the file's header.

A downstream consumer that assumes the normalized shape (e.g. reads
`item["tags"]` or `item["date"]`, or `item["link"]` on an HTML-fallback item)
will `KeyError` on any non-JSON import.

## Evidence
- `personal_index/content_importer.py:48` — `_import_json` is the ONLY handler
  that calls `self._normalize_items(parsed)`.
- `personal_index/content_importer.py:66-68` — HTML fallback appends
  `{"title": clean, "description": desc, "id": ...}` (no `link`).
- `personal_index/content_importer.py:99` — Markdown appends
  `{"title": title, "link": link, "id": ...}` (no `tags`/`date`).
- `personal_index/content_importer.py:119-126` — RSS appends
  `{"title","description","link","id"}` (no `tags`/`date`).
- `personal_index/content_importer.py:131-135` — CSV appends
  `{k: v for k, v in row.items() if v}` + `setdefault("id", ...)` (no
  `tags`/`date`; keys = header columns).
- `personal_index/content_importer.py:137-153` — `_normalize_items` is the
  only place `tags`/`date` are ever set.

## Public contract (target state)
- `import_content(data, fmt) -> list[dict[str, Any]]` MUST return items with a
  **uniform** key set for ALL five formats: every item dict contains exactly
  `title: str`, `description: str`, `link: str`, `id: str`, `tags: list[str]`,
  `date: str | None` (the `_normalize_items` shape).
- The cleanest fix: route **every** `_import_{fmt}` handler's output through
  `_normalize_items` before returning (i.e. `import_content` normalizes the
  handler result, or each handler calls it). This makes the HTML-fallback
  `link` default to `""`, and adds `tags=[]` / `date=None` to every non-JSON
  item.
- Behavior that MUST be preserved: JSON single-object wrapping, JSON
  `ValueError` on malformed input, the unsupported-format `ValueError`, and
  the per-format title/link/description extraction semantics (only the key
  *set* changes, not the extracted values).

## Acceptance criteria
1. For each of the five formats, every returned item dict has exactly the keys
   `{"title","description","link","id","tags","date"}` (no missing keys, no
   extra keys).
2. `import_content("<h2>T</h2><p>D</p>", "html")` (fallback path) returns an
   item whose `link == ""` and `tags == []` and `date is None` (previously the
   `link` key was absent).
3. `import_content("# T\n\nbody", "markdown")` returns an item with
   `tags == []` and `date is None`.
4. Existing `tests/test_content_importer.py` happy-path assertions on
   `title`/`description`/`link`/`id` values stay green (values unchanged; only
   the key set is completed).

## Pinning tests to add
- `test_all_formats_uniform_key_set` — for each of json/html/markdown/rss/csv,
  assert `set(item.keys()) == {"title","description","link","id","tags","date"}`
  for every returned item (normal case across all five formats).
- `test_html_fallback_has_link_and_tags` (guard path: no `<article>` in the
  HTML, so the fallback branch runs) — assert the fallback item has
  `link == ""`, `tags == []`, `date is None` alongside a normal
  `<article>`-based item that carries a real `link`.

## Docs
`docs/content-importer.md` (this cycle) documents the hole; the implementer
keeps the page true when fixing (mark contract hole 1 RESOLVED and update the
per-format item-shape lines to state the uniform normalized shape).
