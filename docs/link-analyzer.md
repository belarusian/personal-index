# link-analyzer — `personal_index.link_analyzer`

Link analysis for crawled pages. Given a page URL and the list of links found
on it, classifies each link as internal or external, tracks anchor-text and
domain distributions, and flags suspicious links. Stdlib-only
(`collections.Counter`, `dataclasses`, `urllib.parse`, `logging`); no I/O, no
network, no disk — every method is a pure in-memory computation over the
input dicts.

## Public API

### `LinkStats` (dataclass)

Statistics about the links on a single page.

| Field | Type | Default |
|-------|------|---------|
| `total_links` | `int` | `0` |
| `internal_links` | `int` | `0` |
| `external_links` | `int` | `0` |
| `unique_domains` | `int` | `0` |
| `broken_links` | `int` | `0` |
| `anchor_text_distribution` | `dict[str, int]` | `{}` |
| `domain_distribution` | `dict[str, int]` | `{}` |

- `total_links` counts every link whose `url` is non-empty (empty-URL links
  are skipped before any counting).
- `internal_links` + `external_links` partition `total_links`: each counted
  link is exactly one or the other (see `_is_internal`).
- `unique_domains` is set to the number of **distinct external** domains
  (`len(domain_counter)`). Despite the name it does **not** include internal
  domains — see Contract Holes.
- `broken_links` is declared but **never written** by `analyze`; it is always
  `0` (see Contract Holes).
- `anchor_text_distribution` / `domain_distribution` are the top-20 entries
  of the respective counters (see `analyze`).

### `LinkAnalysisResult` (dataclass)

Result of analyzing one page.

| Field | Type | Default |
|-------|------|---------|
| `url` | `str` | — |
| `stats` | `LinkStats` | — |
| `top_anchor_texts` | `list[tuple[str, int]]` | `[]` |
| `top_domains` | `list[tuple[str, int]]` | `[]` |
| `suspicious_links` | `list[str]` | `[]` |
| `all_external_domains` | `set[str]` | `set()` |

- `top_anchor_texts` is `anchor_counter.most_common(10)` — the top-10 anchor
  texts with counts (a list of `(text, count)` tuples, most common first).
- `top_domains` is `domain_counter.most_common(10)` — the top-10 external
  domains with counts.
- `suspicious_links` is the list of link URLs flagged by `_is_suspicious`, in
  encounter order.

### `LinkAnalyzer`

`LinkAnalyzer(base_domain: str = "", max_anchor_length: int = 100)`

- `base_domain` — the domain treated as "internal". When empty (the default),
  **no** link is internal; every non-empty link is external.
- `max_anchor_length` — anchor text is truncated to this many characters
  before counting. A non-positive value is not validated (see Contract
  Holes).

#### `analyze(url: str, links: list[dict]) -> LinkAnalysisResult`

Analyze the links found on one page.

- Iterates `links`; each link is a dict read via `link.get("url", "")` and
  `link.get("text", "")`. A link whose `url` is empty (or absent) is **skipped
  entirely** — it is not counted in `total_links` and is not classified.
- For each remaining link (`_analyze_single_link`):
  - `stats.total_links += 1`.
  - Classified via `_is_internal`: internal → `stats.internal_links += 1`;
    otherwise `stats.external_links += 1` **and**, if the parsed `netloc` is
    non-empty, `domain_counter[netloc.lower()] += 1`.
  - Anchor text is `anchor.strip()`; if non-empty, the truncated
    `anchor[:max_anchor_length]` increments `anchor_counter`.
  - If `_is_suspicious(link_url, anchor)` is true, `link_url` is appended to
    the suspicious list.
- After the loop: `stats.unique_domains = len(domain_counter)` (distinct
  external domains), `stats.anchor_text_distribution =
  dict(anchor_counter.most_common(20))`, `stats.domain_distribution =
  dict(domain_counter.most_common(20))`.
- Returns a `LinkAnalysisResult` whose `top_anchor_texts` / `top_domains` are
  the top-10 entries and `suspicious_links` is the flagged list.

#### `analyze_batch(pages: list[dict]) -> list[LinkAnalysisResult]`

Maps each page dict through `analyze`, reading `page.get("url", "")` and
`page.get("links", [])`. Returns one `LinkAnalysisResult` per page, in input
order. A page with no `links` key yields an all-zero result (empty-URL links
skipped).

#### `get_aggregate_stats(results: list[LinkAnalysisResult]) -> dict`

Aggregate statistics across multiple analyses. Returns a dict with:

| Key | Computation |
|-----|-------------|
| `pages_analyzed` | `len(results)` |
| `total_links` | `sum(r.stats.total_links)` |
| `internal_links` | `sum(r.stats.internal_links)` |
| `external_links` | `sum(r.stats.external_links)` |
| `unique_external_domains` | `len(union of r.all_external_domains)` |
| `total_suspicious` | `sum(len(r.suspicious_links))` |

> `unique_external_domains` is the **true cross-page DISTINCT count**
> of external domains — the set-union of the full per-page
> `all_external_domains` sets — NOT a per-page sum and NOT derived from
> the top-20-truncated `domain_distribution`. `test_aggregate_sums == 2`
> is the correct pinned contract. See Contract Holes (DECIDED) and
> `tickets/ARCH-56.md` (Architect Decision, cycle 225).

#### `_is_internal(url: str) -> bool` (private)

Returns `False` when `base_domain` is empty. Otherwise returns
`urlparse(url).netloc.lower() == base_domain.lower()` — an **exact,
case-insensitive netloc match** (no subdomain / suffix matching).

#### `_is_suspicious(url: str, anchor: str) -> bool` (private)

Returns `True` if any of:
- the anchor is empty after `strip()`;
- `anchor.lower().strip()` is in the generic set
  `{"click here", "link", "here", "read more", "more", "this"}`;
- `len(url) > 500`.

## Contract Holes

**Single most important hole — `get_aggregate_stats` undercounts
`unique_external_domains` because it unions a truncated distribution.**
**DECIDED (cycle 225):** the architect decision is option (b) — the true
cross-page distinct count via `all_external_domains`; the fix is
specified in `tickets/ARCH-56.md` (Architect Decision + Public contract
sections). The defect is not yet fixed in code (the implementer has not
landed the change); the pushback (IMPL-6) is resolved by this decision.
`analyze` stores only the **top-20** external domains in
`stats.domain_distribution` (`dict(domain_counter.most_common(20))`), but
`get_aggregate_stats` computes `unique_external_domains` as the size of the
union of `r.stats.domain_distribution.keys()` across all results. When any
page in the batch has more than 20 distinct external domains, the 21st and
beyond are dropped from `domain_distribution` and are therefore **never seen
by the aggregate**, so `unique_external_domains` is silently smaller than the
true number of distinct external domains. The per-page
`LinkStats.unique_domains` field is correct (it is `len(domain_counter)`, the
full count) — only the cross-page aggregate is wrong, which makes the bug
easy to miss: a single-page analysis looks right, and the aggregate is only
wrong once a page exceeds the top-20 cap. See `tickets/ARCH-56.md`.

Secondary (documented here, not ticketed):
- `LinkStats.broken_links` is declared but never written by `analyze`; it is
  always `0`. There is no broken-link detection in this module.
- `LinkStats.unique_domains` is named as if it counts all domains, but it is
  set to `len(domain_counter)` — the count of **external** domains only
  (internal links never feed `domain_counter`).
- `max_anchor_length` is not validated: a non-positive value (e.g. `0` or
  `-1`) is accepted and silently truncates every anchor to the empty string
  (`anchor[:0]` / `anchor[:-1]`), so `anchor_text_distribution` ends up empty
  with no error.
