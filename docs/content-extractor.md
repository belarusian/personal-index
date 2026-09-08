# Content Extractor (spec)

`personal_index.content_extractor` — turns an HTML string into a structured
`ExtractedContent` dataclass and scores its "richness". It is a pure
in-memory module: **no network I/O, no file I/O**. HTML parsing uses
`BeautifulSoup` with the `html.parser` backend (never `lxml`).

The module exports two names: `ExtractedContent` (a `@dataclass`) and
`ContentExtractor`.

## Public API

### `ExtractedContent`
A `@dataclass` describing the content extracted from one HTML page.

Fields (all have defaults, so `ExtractedContent()` is a valid empty result):
- `title: str = ""` — page title (`og:title` preferred over `<title>`).
- `text: str = ""` — visible body text, whitespace-normalized and truncated
  to `max_text_length` (see contract hole 2).
- `meta_description: str = ""` — `<meta name="description">` content.
- `meta_keywords: list[str] = field(default_factory=list)` —
  `<meta name="keywords">` content, comma-split, stripped, empties dropped.
- `headings: list[str] = field(default_factory=list)` — `h1`–`h6` text,
  non-empty only, in document order.
- `links: list[tuple[str, str]] = field(default_factory=list)` —
  `(text, href)` tuples for every `<a href>` with a non-empty `href`.
- `images: list[tuple[str, str]] = field(default_factory=list)` —
  `(alt, src)` tuples for every `<img>` with a non-empty `src`.
- `canonical_url: str = ""` — `<link rel="canonical">` href.
- `language: str = ""` — `<html lang>` attribute.
- `author: str = ""` — `<meta name="author">` content.
- `word_count: int = 0` — `len(text.split())` computed on the **pre-truncation**
  text (see contract hole 2).

### `ContentExtractor`
Stateful only in that it holds `max_text_length`.

#### `__init__(self, max_text_length: int = 100000) -> None`
Stores `max_text_length` (the character cap applied to `text`).

#### `extract(self, html: str) -> ExtractedContent`
- **Guard path (empty/falsy `html`):** returns `ExtractedContent()` with every
  field at its default — no parsing is performed.
- **Normal path:** parses `html` with BeautifulSoup and populates:
  - `title` — `og:title` content if present and non-empty, else the `<title>`
    tag's `.string` if present and non-empty, else `""`.
  - `meta_description`, `author` — via `_extract_meta` (`name="description"` /
    `name="author"`).
  - `meta_keywords` — via `_extract_meta_keywords`.
  - `canonical_url` — via `_extract_canonical`.
  - `language` — via `_extract_language`.
  - Then decomposes every `script`, `style`, `noscript`, and `title` tag so
    the page title is not double-counted in the visible body text.
  - `headings` — via `_extract_headings`.
  - `links` — via `_extract_links`.
  - `images` — via `_extract_images`.
  - `text` — via `_extract_text` (whitespace-normalized, truncated to
    `max_text_length`).
  - `word_count` — `len(text.split())` where `text` is the **pre-truncation**
    normalized text (see contract hole 2).

#### `extract_readability_score(self, content: ExtractedContent) -> float`
Computes a content-richness score in `[0.0, 1.0]` from three components:
`min(words/500, 0.4) + min(len(headings)*0.1, 0.3) + 0.3 if meta_description`.
- **Guard path (empty text):** `content.text` falsy → returns `0.0`.
- **Guard path (short text):** `len(content.text.split()) < 50` → returns
  `0.0`. Note this recomputes the word count from `content.text` and does
  **not** read `content.word_count` (see contract hole 1).
- **Normal path:** sums the three components and caps at `1.0`.

### Private helpers (not part of the public contract)
`_extract_title`, `_extract_meta`, `_extract_meta_keywords`,
`_extract_canonical`, `_extract_language`, `_extract_headings`,
`_extract_links`, `_extract_images`, `_extract_text` — each operates on a
`BeautifulSoup` object and returns the single field it populates.

## Contract holes
1. **`extract_readability_score` ignores the `word_count` field.** The
   docstring says "Returns 0.0 if text is empty or `word_count < 50`", but the
   body recomputes `words = content.text.split()` and checks `len(words) < 50`
   — it never reads `content.word_count`. For an `ExtractedContent` built by
   `extract()` the two agree, but for a hand-built object (or one whose
   `word_count` was set independently) the guard and the length component can
   diverge from the documented `word_count` field. The contract should either
   use `content.word_count` or the docstring should state that the score is
   derived from `content.text`, not the `word_count` field. (Most important
   hole — ticketed as **ARCH-26**.)
2. **`word_count` is computed on pre-truncation text; the score uses
   post-truncation text.** `extract()` sets `word_count = len(text.split())`
   on the normalized text **before** `_extract_text` truncates it to
   `max_text_length`, but `extract_readability_score` re-splits the
   (possibly truncated) `content.text`. For a page whose normalized text
   exceeds `max_text_length`, `word_count` overstates the word count the score
   actually sees. The two fields are not mutually consistent under truncation.
3. **`title` uses `<title>.string`, not `.get_text()`.** `_extract_title`
   falls back to `title_tag.string`, which is `None` when the `<title>` tag
   contains nested markup (e.g. `<title><span>Foo</span></title>`), so such a
   title is silently dropped to `""` even though visible text exists.

## Tests
`tests/test_content_extractor.py` pins the `extract` guard path (empty `html`),
the per-field extraction (title / og:title / meta / keywords / headings / links /
images / canonical / language / author), the title-not-leaked-into-text
behavior, `max_text_length` truncation, and the readability-score guard +
exact-component paths. The `word_count`-vs-`text` divergence (contract hole 1)
is **not** currently pinned — see ARCH-26.
