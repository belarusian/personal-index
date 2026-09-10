# Content Sitemap (spec)

`personal_index.sitemap` (parser) and `personal_index.sitemap_builder`
(builder) — the "crawl" stage's sitemap component of the
crawl→filter→score→tag→index pipeline. The parser reads a raw sitemap XML
string (or a plain-text sitemap) and returns a structured `Sitemap` whose
entries are `SitemapEntry` objects (loc, lastmod, changefreq, priority) and
whose `sitemaps` list holds nested sitemap-index URLs. The builder does the
reverse: it accumulates `SitemapEntry` objects and serializes them to sitemap
XML bytes (or a sitemap-index XML). Neither module does **network I/O** —
fetching the sitemap bytes is the pipeline's job; these modules only parse
and serialize.

The two modules are independent: `sitemap.py` exports `SitemapEntry`,
`Sitemap`, `SitemapParser`; `sitemap_builder.py` exports its **own**
`SitemapEntry` (a different class, see contract hole 2) and `SitemapBuilder`.

## Public API — `personal_index.sitemap` (parser)

### `SitemapEntry` (dataclass)
A single URL entry parsed from a sitemap. Fields, in order:
- `loc: str` — the URL (no default; required).
- `lastmod: str | None = None` — the `<lastmod>` text, or `None` when absent
  or empty (not `""`).
- `changefreq: str = "monthly"` — the `<changefreq>` text, or `"monthly"`
  when absent or empty.
- `priority: float = 0.5` — the `<priority>` text parsed to float, or `0.5`
  when absent, empty, or not a valid float (see contract hole 5: **not
  clamped** to `[0.0, 1.0]`).

- `is_valid() -> bool` — `True` iff `loc` is truthy **and** starts with
  `http://` or `https://`. A relative or `ftp://`/`file://` loc is invalid.

### `Sitemap` (dataclass)
A parsed sitemap. Fields, in order:
- `entries: list[SitemapEntry] = []` — the parsed `<url>` entries, in
  document order.
- `sitemaps: list[str] = []` — nested sitemap URLs from a sitemap index
  (resolved against `source_url` when relative).
- `source_url: str = ""` — the `source_url` passed to `parse` (echoed
  verbatim).

- `url_count -> int` (property) — `len(self.entries)`.
- `sitemap_count -> int` (property) — `len(self.sitemaps)`.
- `get_urls() -> list[str]` — `[e.loc for e in self.entries if e.is_valid()]`
  — only entries with a valid `http://`/`https://` loc.

### `SitemapParser`
Stateless parser (no instance state beyond the `NAMESPACES` class constant
`{"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}`).

- `parse(xml_content: str, source_url: str = "") -> Sitemap`
  - **Guard path 1:** empty `xml_content` (`""` / falsy) → returns an empty
    `Sitemap(source_url=source_url)`.
  - **Guard path 2:** XML that fails to parse (`defusedxml` `ParseError`) →
    returns an empty `Sitemap(source_url=source_url)`.
  - Otherwise: parses the root with `defusedxml`, strips any `{ns}` prefix
    from the root tag (splits on `}`), and dispatches:
    - bare root tag `"sitemapindex"` → `_parse_sitemap_index_items(root, ...)`.
    - else, if the root contains a `ns:sitemapindex` child →
      `_parse_sitemap_index_items(child, ...)`.
    - else: iterates the `ns:url` children, appending each non-`None`
      `_parse_url_element` result to `sitemap.entries`.
  - `sitemap.source_url` is set to `source_url` on the returned object in all
    paths. **Note:** a root tag that is neither `sitemapindex` nor a
    `<urlset>`-style container (e.g. `<html>`) falls through to the `ns:url`
    loop, finds no `ns:url` children, and returns an empty `Sitemap` with no
    signal that the input was not a sitemap (see contract hole 1).

- `parse_text_sitemap(text: str, base_url: str = "") -> Sitemap`
  - **Guard path:** empty `text` → returns an empty `Sitemap(source_url=base_url)`.
  - Otherwise: splits `text.strip()` on `"\n"`; for each line, strips it,
    skips blank lines and lines starting with `#`; if `base_url` is set and
    the line is not `http://`/`https://`, resolves it with `urljoin`; builds a
    `SitemapEntry(loc=line)` and appends it **only if `is_valid()`** (so
    relative lines with no `base_url`, and non-http lines, are dropped).
  - `lastmod`/`changefreq`/`priority` are left at their defaults (text
    sitemaps carry no such metadata).

- `filter_by_priority(sitemap: Sitemap, min_priority: float = 0.5) -> list[SitemapEntry]`
  — `[e for e in sitemap.entries if e.priority >= min_priority]` (inclusive
  boundary).
- `filter_by_changefreq(sitemap: Sitemap, freq: str = "daily") -> list[SitemapEntry]`
  — `[e for e in sitemap.entries if e.changefreq == freq]` (exact string
  match). **Note:** the default `freq="daily"` does not match the entry
  default `changefreq="monthly"`, so a bare call returns only explicitly-
  `daily` entries (see contract hole 6).
- `get_recent_entries(sitemap: Sitemap, days: int = 30) -> list[SitemapEntry]`
  - `cutoff = datetime.now(timezone.utc)`. Iterates `sitemap.entries` in order.
  - Entries whose `lastmod` is falsy (`None` or `""`) are **skipped**.
  - Each remaining `lastmod` is parsed with `datetime.fromisoformat` after
    replacing a trailing `"Z"` with `"+00:00"`; entries whose `lastmod` raises
    `ValueError` or `TypeError` are **skipped** (no exception propagates).
  - An entry is included when `(cutoff - lastmod).days <= days` (inclusive
    boundary). Returns the collected entries as a new list.

### Private methods (documented for contract completeness)
- `_resolve_sitemap_url(loc, source_url) -> str` — `urljoin(source_url, loc)`
  when `source_url` is set and `loc` is not `http://`/`https://`; else `loc`.
- `_parse_sitemap_index_items(root, sitemap, source_url) -> None` — for each
  `ns:sitemap` element, reads `ns:loc` (if present and non-empty), resolves it
  against `source_url`, and appends to `sitemap.sitemaps`. **Fallback:** if
  `sitemap.sitemaps` is still empty, retries with plain (un-namespaced)
  `sitemap`/`loc` tags.
- `_parse_url_element(url_elem, base_url="") -> SitemapEntry | None` — reads
  `ns:loc` (returns `None` if absent or empty); resolves a relative loc
  against `base_url`; reads `ns:lastmod` (→ `lastmod`, `None` if absent),
  `ns:changefreq` (→ `changefreq`, `"monthly"` if absent), `ns:priority`
  (→ `priority`, `0.5` default; `float()` under `suppress(ValueError)` —
  **no clamping**).

## Public API — `personal_index.sitemap_builder` (builder)

Module constants: `SM_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"`,
`NSMAP = {"": SM_NS}`.

### `SitemapEntry` (plain class — **not** a dataclass, and **not** the
`sitemap.SitemapEntry` above; see contract hole 2)
- `__init__(url: str, last_modified: datetime | None = None,
  change_frequency: str = "monthly", priority: float = 0.5)`
  - `self.url = url`.
  - `self.last_modified = last_modified or datetime.now(timezone.utc)` —
    **auto-filled to the current UTC time when `None`** (so a built sitemap
    always carries a `lastmod`, and it is the build-time, not the content's
    actual last-modified).
  - `self.change_frequency = change_frequency`.
  - `self.priority = max(0.0, min(1.0, priority))` — **clamped** to
    `[0.0, 1.0]` (unlike the parser's `SitemapEntry`, see contract hole 5).
- `to_element() -> Element` — a `<url>` element with exactly four
  sub-elements: `loc` (text = `self.url`), `lastmod` (text =
  `self.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")`), `changefreq` (text =
  `self.change_frequency`), `priority` (text = `f"{self.priority:.1f}"`, one
  decimal place).

### `SitemapBuilder`
- Class constants: `MAX_URLS_PER_SITEMAP = 50_000` (the default
  `chunk_size` for `split_into_chunks`), `MAX_SITEMAP_SIZE_BYTES = 50 * 1024 * 1024`
  (50 MB, the default `max_bytes` for `split_by_size`). The URL-count limit
  is enforced by `split_into_chunks`; the byte-size limit is enforced by
  `split_by_size`. `build()` enforces neither (see its entry below).
- `__init__(domain: str = "")` — `self.domain = domain`, `self.entries = []`.
- `add_entry(url, last_modified=None, change_frequency="monthly",
  priority=0.5) -> None` — appends a new `SitemapEntry` (auto-fills
  `last_modified`, clamps `priority`).
- `add_entries(entries: list[SitemapEntry]) -> None` — `self.entries.extend`
  in order (no copy, no de-duplication).
- `build() -> bytes` — a `<urlset>` root (with the sitemap namespace), one
  `to_element()` per entry, serialized with `tostring(..., encoding="unicode",
  xml_declaration=False)`, prefixed with `<?xml version="1.0" encoding="UTF-8"?>\n`,
  returned as UTF-8 bytes. **Enforces no size limit** (neither the URL-count
  nor the byte-size limit) — it serializes every entry unconditionally; a
  caller who needs to respect either limit must split first (`split_into_chunks`
  for URL count, `split_by_size` for byte size) and build each chunk.
- `build_sitemap_index(sitemap_urls: list[str]) -> bytes` — a `<sitemapindex>`
  root with one `<sitemap><loc>` per URL, same XML-declaration prefix, UTF-8
  bytes.
- `split_into_chunks(chunk_size: int = MAX_URLS_PER_SITEMAP) -> list[list[SitemapEntry]]`
  — `[self.entries[i:i+chunk_size] for i in range(0, len(self.entries), chunk_size)]`
  — splits **by URL count only** (enforces `MAX_URLS_PER_SITEMAP`, not the
  byte-size limit). **Guard path:** `chunk_size <= 0` raises
  `ValueError` from `range()` (see contract hole 4).
- `split_by_size(max_bytes: int = MAX_SITEMAP_SIZE_BYTES) -> list[list[SitemapEntry]]`
  — measures each entry's serialized length and breaks a chunk when adding the
  next entry would push the chunk past `max_bytes` (the fixed per-chunk wrapper
  overhead is measured once via a single `build()` call). **Enforces the
  `MAX_SITEMAP_SIZE_BYTES` byte budget** — a chunk returned here serializes to at
  most `max_bytes` bytes when passed to `build()`. A single entry larger than
  `max_bytes` still gets its own chunk; an empty builder returns `[]`.
- `clear() -> None` — `self.entries.clear()` (in place).
- `url_count -> int` (property) — `len(self.entries)`.

## Invariants
- `parse` / `parse_text_sitemap` never raise on malformed or non-sitemap
  input — every failure path returns an (empty) `Sitemap`.
- `url_count == len(entries)` and `sitemap_count == len(sitemaps)` always.
- `get_urls()` returns only entries whose `loc` is `http://`/`https://`.
- `get_recent_entries` never raises on a bad `lastmod` — unparseable entries
  are silently skipped.
- Builder `priority` is always within `[0.0, 1.0]` after construction.
- Builder `last_modified` is never `None` (auto-filled to UTC now).

## Side effects
- **Parser:** none. `SitemapParser` is pure — it reads the input string and
  returns new `Sitemap`/`SitemapEntry` objects. No I/O, no mutation of shared
  state, no logging.
- **Builder:** `SitemapBuilder` mutates its own `self.entries` list in place
  (`add_entry`/`add_entries`/`clear`). `build()`/`build_sitemap_index()` are
  pure reads of that list. The builder's `SitemapEntry.__init__` reads
  `datetime.now(timezone.utc)` when `last_modified` is `None` (a wall-clock
  read, not I/O). No network, no file, no logging.

## Contract holes

1. **`MAX_SITEMAP_SIZE_BYTES` is declared but never enforced — RESOLVED
   (ARCH-22):** the builder shipped `MAX_SITEMAP_SIZE_BYTES = 50 * 1024 * 1024`
   (50 MB) as a class constant, but `build()` and `split_into_chunks()` split
   **only by URL count** (`MAX_URLS_PER_SITEMAP = 50_000`); nothing measured the
   serialized byte length, so a sitemap with, e.g., 49,999 URLs each carrying a
   long `loc`/`lastmod` could silently exceed the 50 MB limit the constant
   advertised. **Fixed (Option A, enforce):** a new `split_by_size(
   max_bytes: int = MAX_SITEMAP_SIZE_BYTES)` measures each entry's serialized
   length (plus the fixed per-chunk wrapper overhead) and breaks a chunk when
   adding the next entry would exceed `max_bytes`, making the constant
   load-bearing. `build()` and `split_into_chunks()` docstrings now state
   exactly which limits are enforced (URL count, byte size) and which are not.

2. **Two `SitemapEntry` classes with the same name but different shapes:**
   `sitemap.SitemapEntry` is a dataclass with fields `loc`/`lastmod`
   (`str | None`)/`changefreq`/`priority`; `sitemap_builder.SitemapEntry` is a
   plain class with fields `url`/`last_modified` (`datetime`, auto-filled)/
   `change_frequency`/`priority`. A reader who imports both (or greps for
   `SitemapEntry`) cannot tell which is which, and the field names
   (`loc` vs `url`, `lastmod` vs `last_modified`, `changefreq` vs
   `change_frequency`) and the `lastmod` type (`str | None` vs `datetime`)
   differ. There is no shared base or alias.

3. **`parse` gives no signal for a non-sitemap root:** like the RSS parser
   (ARCH-21), `parse` returns an empty `Sitemap` when the root tag is neither
   `sitemapindex` nor a `<urlset>`-style container (e.g. `<html>`), with no
   exception, flag, or other signal. A caller cannot distinguish "a valid
   sitemap with zero URLs" from "this was not a sitemap at all". (Same class
   as ARCH-21; not re-ticketed here as a separate hole.)

4. **`split_into_chunks(chunk_size <= 0)` raises `ValueError`:** the default
   is safe, but a caller passing `chunk_size=0` (or a negative value) hits
   `range(0, n, 0)` → `ValueError: range() arg 3 must not be zero`. The
   guard path is undocumented and unhandled.

5. **Priority clamping is asymmetric between the two modules:** the builder
   clamps `priority` to `[0.0, 1.0]`, but the parser's `_parse_url_element`
   does `float(priority_elem.text)` under `suppress(ValueError)` with **no
   clamping**, so a sitemap carrying `priority="5.0"` yields
   `SitemapEntry.priority = 5.0`. `filter_by_priority(min_priority=0.5)` then
   treats such an entry as high-priority. The two `SitemapEntry` types do not
   agree on the valid range.

6. **`filter_by_changefreq` default does not match the entry default:** the
   method default is `freq="daily"` but the `SitemapEntry` default is
   `changefreq="monthly"`, so a bare `filter_by_changefreq(sitemap)` returns
   only explicitly-`daily` entries and silently drops the default-`monthly`
   ones. The mismatched defaults are undocumented.
