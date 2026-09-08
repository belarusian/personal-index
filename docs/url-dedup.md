# url_dedup — Exact Contract

Module: `personal_index/url_dedup.py` (232 lines)

Deduplicates URLs using normalization plus same-domain fuzzy path matching.
Two public types: `DedupResult` (a dataclass) and `URLDeduplicator` (a plain
class). State is two dicts: `_seen_urls: dict[str, str]` (normalized →
original, insertion-ordered) and `_url_groups: dict[str, list[str]]`
(domain → list of **original** URLs, insertion-ordered). Only
**non-duplicate** URLs are ever stored (see contract holes).

## Public API

### DedupResult

A `@dataclass` with five fields:

- `is_duplicate: bool`
- `original_url: str`
- `matched_url: str | None = None`
- `similarity_score: float = 0.0`
- `reason: str = ""`

`reason` is one of `"exact_match"`, `"fuzzy_match"`, or `"unique"`.

### URLDeduplicator

State: `_seen_urls` (normalized → original) and `_url_groups` (domain →
original URLs). Both are populated **only** by `add_url` for URLs that are
not duplicates.

#### Constructor

- `__init__(self, fuzzy_threshold: float = 0.95) -> None`
  Sets `_seen_urls = {}`, `_fuzzy_threshold = fuzzy_threshold`,
  `_url_groups = {}`. No validation of `fuzzy_threshold` (a value `> 1.0`
  makes fuzzy matching impossible; a value `<= 0.0` matches everything —
  see contract holes).

#### Properties

- `seen_count(self) -> int`
  `len(self._seen_urls)` — number of **distinct non-duplicate** URLs stored
  so far. Read-only; does not mutate state.

#### Normalization

- `normalize_url(self, url: str) -> str`
  Applies, in order: (1) drop the fragment; (2) strip a trailing slash from a
  non-root path; (3) sort query parameters alphabetically, keeping only the
  **first** value of each key; (4) lowercase the scheme and netloc; (5) remove
  a leading `www.` from the netloc; (6) remove tracking parameters
  (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`,
  `fbclid`, `gclid`). Returns the normalized URL string.

  Private helpers (each a `@staticmethod`): `_strip_trailing_slash`,
  `_sort_query_params`, `_lowercase_scheme_netloc`, `_remove_www`,
  `_remove_tracking_params`. `_get_path(url)` returns
  `urlparse(url).path.rstrip("/") or "/"`.

#### Checking and adding

- `check_duplicate(self, url: str) -> DedupResult`
  Pure read (does **not** store). Returns:
  - `is_duplicate=True, reason="exact_match", similarity_score=1.0,
    matched_url=<first-seen original>` when `normalize_url(url)` is already a
    key in `_seen_urls`.
  - `is_duplicate=True, reason="fuzzy_match", similarity_score=<ratio>` when
    the URL's domain (lowercased, `www.`-stripped) is in `_url_groups` and the
    best `difflib.SequenceMatcher(None, path, candidate_path).ratio()` over
    that domain's stored URLs is `>= _fuzzy_threshold` (strictly greater than
    the running best). `matched_url` is that candidate's **original** URL.
  - `is_duplicate=False, reason="unique", similarity_score=0.0` otherwise.

- `add_url(self, url: str) -> DedupResult`
  Calls `check_duplicate(url)`. If the result is **not** a duplicate, stores
  `normalize_url(url) -> url` in `_seen_urls` and appends the **original**
  `url` to `_url_groups[domain]` (creating the domain list if needed).
  Returns the `DedupResult` unchanged. **Duplicate URLs are never stored.**

- `deduplicate_urls(self, urls: list[str]) -> tuple[list[str], list[DedupResult]]`
  Feeds each URL through `add_url` in order. Returns `(unique_urls, results)`
  where `unique_urls` is the list of non-duplicate **original** URLs in input
  order and `results` is the per-URL `DedupResult` list (same order).

#### Introspection

- `get_duplicates(self) -> dict[str, list[str]]`
  For each **stored** original URL, compares its path against every other
  stored URL in the same domain and groups those with
  `SequenceMatcher.ratio() >= _fuzzy_threshold` under the stored original.
  **See contract holes: this can never report the duplicates actually
  detected, because only non-duplicates are stored.**

- `get_stats(self) -> dict`
  `{"total_seen": seen_count, "total_domains": len(_url_groups),
  "total_duplicate_groups": len(get_duplicates())}`.

- `get_canonical_url(self, url: str) -> str | None`
  `self._seen_urls.get(normalize_url(url))` — the first-seen original for an
  exact-normalized match, or `None`.

- `get_domain_urls(self, domain: str) -> list[str]`
  `self._url_groups.get(domain.lower().removeprefix("www."), [])` — the
  stored original URLs for a domain, or `[]`.

- `clear(self) -> None`
  Empties both `_seen_urls` and `_url_groups`.

## Contract Holes

### (ARCH-36) `get_duplicates` / `get_stats` can never report the duplicates actually detected — the dedup record is silently discarded

`add_url` stores a URL **only when it is not a duplicate** (the `if not
result.is_duplicate:` guard). The add-time fuzzy check in `check_duplicate`
guarantees that, within a single domain, every stored URL is pairwise
`< _fuzzy_threshold` from every other stored URL (a URL that would score
`>= threshold` against an already-stored URL is rejected and never stored).
`get_duplicates` then re-scans **only the stored URLs** and reports pairs
scoring `>= _fuzzy_threshold`. By the invariant above, no two stored URLs in
a domain can ever score `>= _fuzzy_threshold`, so `get_duplicates` returns
`{}` for every input the deduplicator actually processed, and
`get_stats()["total_duplicate_groups"]` is always `0`.

The duplicates the module *does* detect (the `fuzzy_match` / `exact_match`
`DedupResult`s returned by `check_duplicate` / `add_url`) are **never
recorded** anywhere in the object's state — they exist only in the transient
`DedupResult` the caller must capture. The docstring promises "Get all
detected duplicates grouped by canonical URL," but the method can only ever
return an empty dict. This is the single most important hole in the module:
the introspection API is structurally dead, so a caller relying on
`get_duplicates` / `get_stats` to audit what was deduplicated gets a silent
false negative.

A defensible contract: `add_url` must **record** each detected duplicate
(normalized → the matched original, with reason and score) in a separate
`_duplicates` structure, and `get_duplicates` must return that recorded map
(grouped by canonical/first-seen URL) rather than re-deriving it from the
non-duplicate-only `_seen_urls`.

### Secondary holes (documented, not separately ticketed)

- **`fuzzy_threshold` is unvalidated.** No bounds check in `__init__`;
  `> 1.0` makes fuzzy matching impossible (only exact matches dedup) and
  `<= 0.0` makes every same-domain URL a fuzzy duplicate of the first.
- **Multi-value query params are dropped.** `normalize_url` keeps only the
  **first** value of each query key (`v[0]`), so `?a=1&a=2` and `?a=1`
  normalize identically and are treated as duplicates.
- **Fuzzy matching is domain-scoped only.** Two near-identical paths on
  different domains are never compared, so cross-domain near-duplicates are
  not detected.
- **`get_canonical_url` is exact-normalized only.** It returns `None` for a
  URL that was deduplicated by *fuzzy* match (its normalized form was never
  stored), so the canonical-URL lookup is blind to fuzzy dedup.
