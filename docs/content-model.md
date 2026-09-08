# Content Model (`personal_index.models`)

Status: **spec** — audited against current code (cycle 169).

The core data models. All are `@dataclass` with `to_dict()` / `from_dict()`
serialization. Enums: `InterestType` (KEYWORD / TOPIC / URL_PATTERN),
`MatchMode` (ANY / ALL / REGEX).

## Interest
Fields: `name`, `interest_type` (default KEYWORD), `value`, `keywords`,
`url_patterns`, `topics`, `priority` (clamped 1-10 in `__post_init__`),
`created_at` (UTC ISO), `enabled` (default True), `topic`, `match_mode`
(default ANY).

- `__post_init__` guard: if `keywords` is passed as an `int` (positional
  priority), it is moved into `priority` and `keywords` reset to `[]`; any
  non-list `keywords` / `url_patterns` / `topics` are reset to `[]`.
- `matches(text, url="") -> bool`: returns False when `not enabled`;
  otherwise True if `value` (lowercased) is a substring of `text`, or any
  `keywords`/`topics` entry (str) is a substring of `text`, or any
  `url_patterns` entry matches `url` via fnmatch (when it contains `*`) or
  `re.search` (invalid regex is skipped).
- `score(text) -> float`: 0.0 when `not enabled`; otherwise the sum of
  `text.count(...)` over `value`, `keywords`, `topics`, multiplied by
  `priority` and capped at `priority * 10`.

## CrawledPage
Fields: `url`, `title`, `content`, `meta_description`, `status_code` (200),
`depth`, `parent_url`, `headers`, `matched_interests`, `relevance_score`,
`crawled_at` (datetime, UTC), `word_count`, `raw_html`, `domain_authority`
(0.5), `language` ("en"), `keywords`.
`from_dict` parses `crawled_at` from ISO string; on `ValueError` or non-datetime
it falls back to `datetime.now(timezone.utc)`.

## IndexedPage
Fields: `url`, `title`, `content`, `keywords`, `matched_interests`,
`crawled_at` (ISO string), `domain`, `status_code` (200), `content_length`,
`language` ("en"), `score` (1.0), `indexed_at`, `source_interest`, `word_count`.
`relevance_score` is a property alias for `score` (getter + setter).
`to_dict` calls `.isoformat()` on any value that has it.

## SearchResult
Fields: `url`, `title`, `snippet`, `relevance_score`, `matched_terms`.

## Page
A generic page model (see `models.py` line 330).

## PipelineStats
Pipeline execution counters (see `models.py` line 461).

## Contract holes
- None found this cycle. The `Interest.__post_init__` int-keywords coercion is
  a documented design constraint (see cycle-1 log), not a defect.

### PipelineStats field drift (contract hole -> ARCH-3) — RESOLVED (cycle 174)
`docs/API_REFERENCE.md` previously documented `PipelineStats` with fields
`pages_filtered_in` and `interests_matched`. The current code (`models.py`
line 461) has `pages_passed_filter` (not `pages_filtered_in`) and **no**
`interests_matched` field. The `docs/API_REFERENCE.md` block was corrected to
match the code exactly (field name, order, `errors: list`), so the doc is no
longer stale. ARCH-3 is closed; the code-side contract docstring + pinning test
landed in the implementer lane (PR #1004).
