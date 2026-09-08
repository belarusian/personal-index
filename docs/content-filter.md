# Content Filter (spec)

`personal_index.content_filter` — the "filter" stage of the
crawl→filter→score→tag→index pipeline. Decides which crawled pages are
included in the index based on content length, title length, domain
blocklist, regex patterns, and interest matching.

## Public API

### `FilterConfig` (dataclass)
Configuration for content filtering. Fields, in order:
- `min_content_length: int = 100` — minimum `len(page.content)` to pass.
- `max_content_length: int = 100000` — maximum `len(page.content)` to pass.
- `min_title_length: int = 3` — minimum `len(page.title)` to pass.
- `require_interest_match: bool = True` — when `True` and an
  `interest_store` is provided, the page must match at least one interest.
- `blocked_domains: list[str] = []` — domains (and their subdomains) to
  reject.
- `blocked_patterns: list[str] = []` — regex patterns; if any matches
  `f"{title} {content}"`, the page is rejected.
- `required_patterns: list[str] = []` — regex patterns; if non-empty and
  NONE match `f"{title} {content}"`, the page is rejected.
- `min_relevance_score: float = 0.0` — when `> 0` and an `interest_store`
  is provided, the page's `total_score` must be at least this value.

### `ContentFilter`
The filter engine.

#### `__init__(self, config: FilterConfig | None = None, interest_store: InterestStore | None = None)`
- Stores `config` (defaults to `FilterConfig()` when `None`).
- Stores `interest_store` (may be `None`).
- Compiles `config.blocked_patterns` into `self._compiled_blocked`
  (list of `re.Pattern`, case-insensitive).
- Compiles `config.required_patterns` into `self._compiled_required`
  (list of `re.Pattern`, case-insensitive).
- **Guard path:** invalid regex patterns are silently dropped (via
  `suppress(re.error)`); the caller receives no indication of which
  patterns failed to compile.

#### `should_include(self, page: CrawledPage) -> bool`
Returns `True` iff `get_filter_reasons(page)` returns an empty list.
No side effects beyond those of `get_filter_reasons`.

#### `get_filter_reasons(self, page: CrawledPage) -> list[str]`
Runs up to eight checks in order, appending one reason string per failure.
Returns the accumulated list (empty when the page passes every check).

Checks, in order:
1. `len(page.content) < config.min_content_length` →
   `"content length ({n}) below minimum ({min})"`
2. `len(page.content) > config.max_content_length` →
   `"content length ({n}) exceeds maximum ({max})"`
3. `len(page.title) < config.min_title_length` →
   `"title too short ({n} < {min})"`
4. `self._is_blocked_domain(page.url)` → `"domain is blocked"`
5. `self._matches_blocked_patterns(page)` → `"content matches blocked pattern"`
6. `self._compiled_required` is non-empty AND
   `not self._matches_required_patterns(page)` →
   `"content does not match required pattern"`
7. `config.require_interest_match` AND `self.interest_store` is not `None`
   AND `not self._matches_interests(page)` → `"no matching interests"`
8. `self.interest_store` is not `None` AND `config.min_relevance_score > 0`
   AND `interest_store.total_score(f"{title} {content}") < min_relevance_score`
   → `"relevance score ({score}) below minimum ({min})"`

**Side effects:** Check 7 calls `_matches_interests`, which on a match
mutates `page.matched_interests` (set to the matched interest names) and
`page.relevance_score` (set to `interest_store.total_score(text)`).
Check 8 re-computes `total_score` independently (does not read
`page.relevance_score`).

**Guard paths:**
- If `interest_store` is `None`, checks 7 and 8 are both skipped.
- If `config.require_interest_match` is `False`, check 7 is skipped.
- If `config.min_relevance_score` is `0.0`, check 8 is skipped.
- If `self._compiled_required` is empty (no valid required patterns),
  check 6 is skipped entirely.
- If `self._compiled_blocked` is empty, check 5 always passes.

#### `filter_pages(self, pages: list[CrawledPage]) -> list[CrawledPage]`
Returns a new list containing only the pages for which `should_include`
returns `True`. Order is preserved.

**Guard path:** empty input list → returns `[]`.

**Side effects:** calls `should_include` (and thus `get_filter_reasons`)
for each page, which may mutate `page.matched_interests` and
`page.relevance_score` on interest matches.

### Private methods (documented for contract completeness)

#### `_compile_patterns(patterns: list[str]) -> list[re.Pattern]` (static)
Compiles each pattern with `re.IGNORECASE`. Invalid patterns (raising
`re.error`) are silently skipped. Returns the list of successfully
compiled patterns.

#### `_is_blocked_domain(self, url: str) -> bool`
Extracts the domain via `url_utils.extract_domain(url)`.
**Guard path:** if `extract_domain` returns `None` (empty or malformed
URL), returns `False` (not blocked).
Otherwise checks exact match or subdomain suffix (`domain.endswith("." + blocked)`)
against each entry in `config.blocked_domains`.

#### `_matches_blocked_patterns(self, page: CrawledPage) -> bool`
Returns `True` if any compiled blocked pattern matches
`f"{page.title} {page.content}"`.

#### `_matches_required_patterns(self, page: CrawledPage) -> bool`
Returns `True` if any compiled required pattern matches
`f"{page.title} {page.content}"`.

#### `_matches_interests(self, page: CrawledPage) -> bool`
**Guard path:** if `self.interest_store` is `None`, returns `True`
(no check performed — the page is not rejected on interest grounds).
Otherwise builds `text = f"{page.title} {page.content}"` and calls
`interest_store.matches_any(text, page.url)`. On a match, sets
`page.matched_interests = [m.name for m in matches]` and
`page.relevance_score = interest_store.total_score(text)`, then returns
`True`. Returns `False` when no interest matches.

## Contract holes

1. **Silent pattern compilation failure (required_patterns safety gap):**
   `_compile_patterns` silently drops invalid regex patterns. For
   `required_patterns`, if ALL provided patterns are invalid,
   `self._compiled_required` is empty, check 6 is skipped, and the filter
   silently accepts pages that should have been rejected. The caller has
   no way to detect that their required patterns were all invalid. This is
   a safety gap: a typo in a required pattern silently disables the check.
   → **ARCH-18** (ticketed).

2. **Side effect in a query method:** `get_filter_reasons` (and by
   extension `should_include` and `filter_pages`) mutates the input
   `CrawledPage` objects (`matched_interests`, `relevance_score`) as a
   side effect of a query. This is documented in `_matches_interests`'s
   docstring but not in the public method contracts. Callers who invoke
   `get_filter_reasons` for diagnostic purposes (without intending to
   filter) will still mutate their page objects.

3. **Unparseable URL passes domain check:** `_is_blocked_domain` returns
   `False` when `extract_domain` returns `None`. A page with an empty or
   malformed URL is never blocked by the domain check. This is likely
   intentional (can't block what you can't parse) but is a guard path
   worth pinning.
