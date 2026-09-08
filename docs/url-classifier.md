# url_classifier — Exact Contract

Module: `personal_index/url_classifier.py` (223 lines)

## Public API

### URLCategory (str, Enum)

| Member | Value |
|--------|-------|
| PAGE | `"page"` |
| API | `"api"` |
| MEDIA | `"media"` |
| DOCUMENT | `"document"` |
| FEED | `"feed"` |
| REDIRECT | `"redirect"` |
| ERROR | `"error"` |
| STATIC | `"static"` |
| UNKNOWN | `"unknown"` |

**Note**: `ERROR` and `UNKNOWN` are defined but **never assigned** by `classify()`.
The default fallback is always `PAGE`. These are dead enum values.

### ClassificationResult (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| url | str | (required) | Preserved as-is from input |
| category | URLCategory | (required) | First matching rule wins |
| confidence | float | 0.5 | Per-rule value (see below) |
| reasons | list[str] | [] | Always single-element list from `classify()` |
| metadata | dict | {} | **Never populated** by `classify()`; always empty |

### URLClassifier

#### ClassVar pattern lists

| Name | Patterns (regex, case-insensitive) |
|------|-------------------------------------|
| API_PATTERNS | `/api/`, `/v\d+/`, `\.json$`, `\.xml$`, `\.yaml$`, `/graphql`, `/rest/` |
| MEDIA_PATTERNS | image exts, audio exts, video exts, `/images/`, `/media/`, `/static/`, `/assets/` |
| DOCUMENT_PATTERNS | doc exts, `/docs/`, `/documents/`, `/files/`, `/downloads/` |
| FEED_PATTERNS | `\.rss$`, `\.atom$`, `/feed`, `/rss`, `/atom`, `/sitemap` |
| STATIC_PATTERNS | `\.css$`, `\.js$`, `\.map$`, `/static/`, `/assets/`, `/vendor/`, `/node_modules/` |
| REDIRECT_PATTERNS | `/redirect` (×2), `/goto`, `\?url=`, `\?redirect=` |

#### `__init__(self) -> None`

Compiles all six pattern lists into `re.Pattern` objects with `re.IGNORECASE`.
No side effects beyond attribute assignment.

#### `classify(self, url: str) -> ClassificationResult`

**Behavior**:
1. `urlparse(url)` → extract `.path`; lowercase both path and full URL.
2. Check rules in **fixed order** (first match wins):

   | Order | Category | Confidence | Reason string |
   |-------|----------|------------|---------------|
   | 1 | REDIRECT | 0.8 | `"matches redirect pattern"` |
   | 2 | FEED | 0.9 | `"matches feed pattern"` |
   | 3 | API | 0.85 | `"matches API pattern"` |
   | 4 | STATIC | 0.9 | `"matches static asset pattern"` |
   | 5 | MEDIA | 0.85 | `"matches media pattern"` |
   | 6 | DOCUMENT | 0.85 | `"matches document pattern"` |

3. If no rule matches: return `ClassificationResult(url=url, category=PAGE, confidence=0.5, reasons=["no specific pattern matched"])`.

**Guard paths**:
- Empty string `""`: `urlparse("")` → path `""`, no pattern matches → PAGE, 0.5.
- Non-URL string (e.g. `"hello"`): same as above → PAGE, 0.5.
- URL with query string: query is part of `full_url` (lowercased) but NOT part of `path`; patterns like `\?url=` match against `full_url` only.

**Never returns None.**

#### `classify_batch(self, urls: list[str]) -> list[ClassificationResult]`

List comprehension over `classify`. Empty list → `[]`.

#### `get_category_counts(self, urls: list[str]) -> dict[str, int]`

Counts by `result.category.value` (the string value, not the enum member).
Empty list → `{}`.

#### Properties (read-only access to compiled patterns)

| Property | Returns |
|----------|---------|
| `api_re` | `list[re.Pattern]` |
| `media_re` | `list[re.Pattern]` |
| `feed_re` | `list[re.Pattern]` |
| `static_re` | `list[re.Pattern]` |
| `redirect_re` | `list[re.Pattern]` |

No property for `doc_re` (DOCUMENT patterns are private-only).

## Contract Holes

### 1. Overlapping `/static/` and `/assets/` patterns (MEDIA vs STATIC)

`/static/` and `/assets/` appear in **both** `MEDIA_PATTERNS` and `STATIC_PATTERNS`.
Because STATIC (order 4) is checked before MEDIA (order 5), any URL containing
`/static/` or `/assets/` is **always** classified as STATIC, never MEDIA — even if
the extension is an image (e.g. `/static/logo.png` → STATIC, not MEDIA).

The MEDIA_PATTERNS entries for `/static/` and `/assets/` are **dead**: they can
never fire because STATIC always wins first.

**Impact**: A user reading `MEDIA_PATTERNS` would expect `/static/photo.jpg` to
be MEDIA. The actual result is STATIC. This is a silent priority trap.

### 2. ERROR and UNKNOWN are dead enum values

`URLCategory.ERROR` and `URLCategory.UNKNOWN` are defined but `classify()` never
assigns either. The fallback is always PAGE. Any code that branches on
`result.category == URLCategory.ERROR` or `== URLCategory.UNKNOWN` will never
match.

### 3. `metadata` field is never populated

`ClassificationResult.metadata` defaults to `{}` and `classify()` never sets it.
The field is structurally present but functionally dead.

### 4. Duplicate `/redirect` pattern

`REDIRECT_PATTERNS` lists `r"/redirect"` twice (positions 1 and 3). No functional
effect (first match short-circuits) but indicates copy-paste or merge artifact.

## Pinning Tests (for ARCH-31)

1. **`/static/` overlap**: `classify("https://example.com/static/logo.png")` →
   category is STATIC (not MEDIA), confidence 0.9.
2. **`/assets/` overlap**: `classify("https://example.com/assets/app.js")` →
   category is STATIC (not MEDIA), confidence 0.9.
3. **Empty string guard**: `classify("")` → category PAGE, confidence 0.5,
   reasons `["no specific pattern matched"]`.
4. **metadata always empty**: for any input, `result.metadata == {}`.
