# Content Scraper (spec)

`personal_index.scraper` — the "crawl" stage's HTML-parsing component of the
crawl→filter→score→tag→index pipeline. Given a raw HTML string and a base URL,
it parses the document with BeautifulSoup and returns a structured
`ScrapedContent` (title, meta, headings, paragraphs, links, images, tables,
clean text, word count, charset). It does **no network I/O** — fetching is the
pipeline's job (`pipeline.py` `_fetch_page`); the scraper only parses.

The module exports three names: `ScraperConfig`, `ScrapedContent`,
`HTMLScraper`.

## Public API

### `ScraperConfig` (dataclass)
Configuration for HTML scraping. Fields, in order:
- `extract_meta: bool = True` — when `True`, extract `<title>`,
  `meta[name=description]`, `meta[name=keywords]`, and the `og:title` /
  `og:description` fallbacks.
- `extract_links: bool = True` — when `True`, extract `<a href>` links.
- `extract_images: bool = True` — when `True`, extract `<img>` sources.
- `extract_headings: bool = True` — when `True`, extract `h1`–`h6` headings.
- `extract_tables: bool = False` — when `True`, extract `<table>` rows.
  **Off by default** (tables are the only extraction gated behind a flag that
  defaults to `False`).
- `remove_scripts: bool = True` — **dead flag** (see contract hole 1): stored
  but never read; script/style/noscript removal is driven by `blocked_tags`.
- `max_content_length: int = 1_000_000` — `raw_text` is truncated to this
  length when longer (see contract hole 2 for the `word_count` interaction).
- `blocked_tags: list[str] = ["script", "style", "noscript"]` — tag names
  decomposed (removed from the tree) before any extraction runs.

### `ScrapedContent` (dataclass)
The return object of `HTMLScraper.scrape`. Fields, in order:
- `url: str = ""` — the `base_url` passed to `scrape` (echoed verbatim).
- `title: str = ""` — from `<title>` (or `og:title` fallback).
- `meta_description: str = ""` — from `meta[name=description]` (or
  `og:description` fallback).
- `meta_keywords: str = ""` — from `meta[name=keywords]`.
- `headings: list[str] = []` — one `"h{level}: {text}"` string per non-empty
  heading, in document order.
- `paragraphs: list[str] = []` — one stripped text string per non-empty `<p>`.
- `links: list[dict] = []` — one `{"url", "text", "title"}` per unique
  absolute link.
- `images: list[dict] = []` — one `{"src", "alt", "width", "height"}` per
  `<img>` with a non-empty `src`.
- `tables: list[dict] = []` — one `{"rows": [[cell, ...], ...]}` per table
  with at least one non-empty row.
- `raw_text: str = ""` — the joined clean text (see `_get_clean_text`).
- `word_count: int = 0` — `len(raw_text.split())` **before** the
  `max_content_length` truncation (see contract hole 2).
- `charset: str = "utf-8"` — detected charset (see `_extract_charset`).

### `HTMLScraper`
The scraper engine.

#### `__init__(self, config: ScraperConfig | None = None)`
Stores `config` (defaults to `ScraperConfig()` when `None`). No I/O.

#### `scrape(self, html: str, base_url: str = "") -> ScrapedContent`
**Guard path:** there is no early-return guard — an empty/`None`-ish `html`
still parses (BeautifulSoup of `""` yields an empty tree) and returns a
`ScrapedContent` with all list fields empty, `raw_text == ""`,
`word_count == 0`, `charset == "utf-8"`, and `url == base_url`.

Otherwise, in order:
1. `soup = BeautifulSoup(html, "html.parser")`; `result = ScrapedContent(url=base_url)`.
2. `_extract_charset(soup, result)` — always runs (not gated by any flag).
3. `_clean_page(soup)` — always runs; decomposes every tag named in
   `config.blocked_tags`.
4. If `config.extract_meta`: `_extract_meta_tags(soup, result)`.
5. If `config.extract_headings`: `_extract_headings(soup, result)`.
6. `_extract_paragraphs(soup, result)` — **always runs** (not gated by a flag).
7. If `config.extract_links`: `_extract_links(soup, result, base_url)`.
8. If `config.extract_images`: `_extract_images(soup, result, base_url)`.
9. If `config.extract_tables`: `_extract_tables(soup, result)`.
10. `result.raw_text = _get_clean_text(soup)`; `result.word_count =
    len(result.raw_text.split())`.
11. If `len(result.raw_text) > config.max_content_length`:
    `result.raw_text = result.raw_text[: config.max_content_length]`
    (**`word_count` is NOT recomputed** — see contract hole 2).
12. Returns `result`.

**Side effects:** none (pure query; the input `html` string is not mutated).

### Private methods (documented for contract completeness)

#### `_extract_charset(self, soup, result) -> None`
Reads `meta[charset]` first (sets `result.charset` to its value, defaulting to
`"utf-8"`), then reads `meta[http-equiv=Content-Type]` and, if its `content`
contains a `charset=...` token, **overwrites** `result.charset` with that
token. So when both metas are present, the `http-equiv` value wins. When
neither is present, `result.charset` stays `"utf-8"`.

#### `_clean_page(self, soup) -> None`
For each name in `config.blocked_tags`, `soup.find_all(name)` and
`tag.decompose()` each match. Mutates the soup in place. Driven by
`blocked_tags` only — `remove_scripts` is not consulted (contract hole 1).

#### `_extract_meta_tags(self, soup, result) -> None`
- `title`: `<title>`'s `.string`, stripped, if present and non-empty.
- `meta_description`: `meta[name=description][content]`, stripped.
- `meta_keywords`: `meta[name=keywords][content]`, stripped.
- `og:title` fallback: `meta[property=og:title][content]`, stripped, **only
  when `result.title` is still empty**.
- `og:description` fallback: `meta[property=og:description][content]`,
  stripped, **only when `result.meta_description` is still empty**.

#### `_extract_headings(self, soup, result) -> None`
For `level` in `1..6`, for each non-empty `h{level}` (by `get_text(strip=True)`),
appends `f"h{level}: {text}"`. Headings are emitted in document order (the
level loop means all `h1`s come before all `h2`s, etc., NOT strict document
order across levels).

#### `_extract_paragraphs(self, soup, result) -> None`
For each non-empty `<p>`, appends its stripped text.

#### `_extract_links(self, soup, result, base_url) -> None`
For each `<a href>` with a non-empty stripped `href`: `absolute =
urljoin(base_url, href)`; **deduplicated** by `absolute` (first occurrence
wins); appends `{"url": absolute, "text": <a text>, "title": <a title or "">}`.

#### `_extract_images(self, soup, result, base_url) -> None`
For each `<img>` with a non-empty `src`: `absolute = urljoin(base_url, src)`;
appends `{"src": absolute, "alt", "width", "height"}` (each attribute `""`
when absent). **Not deduplicated** (unlike links).

#### `_extract_tables(self, soup, result) -> None`
For each `<table>`: collect rows; each row is the list of stripped
`td`/`th` texts; a row is kept only if it has at least one cell; a table is
appended only if it has at least one kept row, as `{"rows": rows}`.

#### `_get_clean_text(self, soup) -> str`
Joins the stripped text of every `p`, `h1`–`h6`, `li`, `td`, `th` element
(space-separated, in document order). This is the source of `raw_text` and
`word_count`.

## Contract holes

1. **Dead `remove_scripts` flag:** `ScraperConfig.remove_scripts` (default
   `True`) is stored but never read anywhere in the module. Script/style/
   noscript removal is driven entirely by `blocked_tags`. A caller who sets
   `remove_scripts=False` expecting scripts to be kept gets no effect — the
   `blocked_tags` default still decomposes them. The flag is a silent no-op.
   → **ARCH-20** (ticketed).

2. **`word_count` inconsistent after truncation:** `word_count` is computed
   from `raw_text` at step 10, *before* the `max_content_length` truncation at
   step 11. When `raw_text` is truncated, `word_count` still reflects the
   pre-truncation text, so `word_count != len(result.raw_text.split())`. A
   caller who relies on `word_count` to describe the returned `raw_text` is
   wrong for long pages. The docstring does not state this ordering.
   → **ARCH-20** (ticketed, same contract).

3. **Charset override order is undocumented:** when both `meta[charset]` and
   `meta[http-equiv=Content-Type]` are present, the `http-equiv` value
   silently wins. This is a reasonable precedence but is not stated, so a
   reader who expects the explicit `charset` attribute to win is surprised.

4. **`HTMLScraper` is a dead component in the shipped pipeline:**
   `pipeline.py` instantiates `self.scraper = HTMLScraper()` (line 170) but
   never calls `.scrape()`; the crawl step (`_fetch_page`) fetches HTML via
   `urllib` and the extract step uses `ContentExtractor`, not the scraper. The
   scraper is exercised only by its own tests, not by the end-to-end pipeline.
   This is a wiring gap, not a scraper defect, but it means the "crawl" stage
   the pipeline advertises does not actually route through this module.

5. **Headings are not in strict document order:** `_extract_headings` loops
   `level 1..6` and appends per level, so the `headings` list groups by level
   (all `h1`s, then all `h2`s, …) rather than preserving document order across
   levels. A page with `<h2>` before `<h1>` reports the `h1` first.
