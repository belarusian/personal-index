# domains — Exact Contract

Module: `personal_index/domains.py` (209 lines, stdlib-only imports:
`json`, `os`, `dataclasses`). Two `@dataclass` types: `DomainRule` (a single
crawl allow/deny rule) and `DomainManager` (the rule store + page-count
accounting + JSON persistence).

> **Disambiguation (near-name collision):** This page documents
> `personal_index.domains` (module `personal_index/domains.py`, classes
> `DomainManager` / `DomainRule` — crawl allow/deny **rules** with JSON
> persistence and per-domain page-count accounting). It is **DIFFERENT** from:
> - `personal_index.url_classifier` (see [url-classifier.md](url-classifier.md), class `URLClassifier` — URL *category* classification, no rules/persistence)
> - `personal_index.url_dedup` (see [url-dedup.md](url-dedup.md), URL *deduplication*, no allow/deny)
> - `personal_index.link_analyzer` (see [link-analyzer.md](link-analyzer.md), class `LinkAnalyzer` — link *stats*, no rules)
> - `personal_index.robots_cache` (see [robots-cache.md](robots-cache.md), class `RobotsCache` — robots.txt *fetch cache*, not a rule store)
>
> Tests import from this module: `from personal_index.domains import
> DomainManager, DomainRule` (see `tests/test_domains.py`,
> `tests/deep/test_domains_adversarial.py`,
> `tests/deep/test_ticket109_save_no_dir.py`).

## Public API

### DomainRule (dataclass, line 11)

Fields: `domain: str`, `allowed: bool = True`, `max_pages: int = 100`,
`max_depth: int = 3`, `reason: str = ""`.

- `to_dict() -> dict` — returns all five fields as a plain dict (no
  normalization, no omission).
- `from_dict(data: dict) -> DomainRule` (classmethod) — **degrades a
  non-mapping `data` to `DomainRule(domain="")`** instead of raising, and
  **filters to the five known keys** (unknown keys are ignored, forward-compat).
  A missing key simply falls back to the field default. This is the defensive
  load path: a single malformed entry cannot fail manager construction.

### DomainManager (dataclass, line 49)

Fields: `rules_file: str | None = None`, plus private `_rules:
dict[str, DomainRule]`, `_page_counts: dict[str, int]`, `_has_whitelist:
bool = False`.

- `__post_init__` — if `rules_file` is set AND the file exists, calls
  `_load()`.
- `_load()` — reads `rules_file` as JSON. On `json.JSONDecodeError` /
  `KeyError` / `TypeError` / `ValueError` it degrades to `_rules = {}`. A
  top-level non-dict JSON value also degrades to `_rules = {}`. Only dict
  values are kept as rules (non-dict values are dropped). After loading it
  **recomputes `_has_whitelist = any(r.allowed for r in _rules.values())`**.
- `_save()` — no-op when `rules_file` is falsy. Otherwise
  `os.makedirs(dirname or ".", exist_ok=True)` then writes the rules as
  indented JSON. **Not atomic** (plain `open(..., "w")`, no temp-file +
  rename), so a crash mid-write can truncate the file; the next `_load`
  then degrades to empty (see contract holes).
- `add_allow(domain, max_pages=100, max_depth=3)` — upserts an allow rule
  (overwrites any existing rule for `domain`, including a block), sets
  `_has_whitelist = True`, saves.
- `add_block(domain, reason="")` — upserts a block rule (overwrites any
  existing rule, including an allow). Does **NOT** touch `_has_whitelist`.
  Saves.
- `is_allowed(domain) -> bool` — if `domain` has a rule: `False` when the
  rule is a block; otherwise `not (page_count >= rule.max_pages)` (the
  `>=` means `max_pages=0` disallows immediately, and reaching exactly
  `max_pages` disallows). If `domain` has **no** rule: returns
  `not self._has_whitelist` (allow-all when no whitelist, deny-all when a
  whitelist is present).
- `is_blocked(domain) -> bool` — `True` only when `domain` has a rule AND
  that rule is a block; `False` for unlisted domains.
- `record_page(domain)` — increments `_page_counts[domain]` (creates at 1).
- `get_page_count(domain) -> int` — `0` when unrecorded.
- `reset_counts()` — clears `_page_counts` (rules untouched).
- `remove(domain) -> bool` — deletes the rule if present and saves, returns
  `True`; returns `False` when absent. **Decided contract (ARCH-84, Option A):**
  after deletion it **recomputes `_has_whitelist = any(r.allowed for r in
  _rules.values())`** (the same expression `_load` uses), so removing the last
  allow rule restores the allow-all default for unlisted domains. (The current
  code does not yet recompute — the fix is pending implementation; see
  "Documented Contract Hole".)
- `list_rules() -> list[DomainRule]` — `list(self._rules.values())`.
- `get_max_depth(domain) -> int` — the rule's `max_depth` when present,
  else the default `3`.

## Invariants

- **Exact-match, case-sensitive** domain keys: no normalization anywhere
  (`"EXAMPLE.com"` is a different key from `"example.com"`).
- **Whitelist semantics**: the presence of *any* allow rule makes the manager
  a whitelist — unlisted domains are then disallowed. A block-only manager is
  **not** a whitelist (unlisted domains stay allowed).
- **`_has_whitelist` is always derived from the rule set** (confirmed contract,
  ARCH-84 Option A): it equals `any(r.allowed for r in _rules.values())`,
  recomputed on load and after every rule removal, and set on every allow — so
  removing the last allow rule restores the allow-all default.
- **Upset is last-write-wins**: `add_allow`/`add_block` overwrite the existing
  rule for a domain; there is no duplicate-domain error.
- **Page counts are in-memory only** — never persisted to `rules_file`; a
  fresh `DomainManager` on the same file starts at count 0.

## Persistence

`rules_file` is a JSON object mapping `domain -> rule-dict` (the five
`DomainRule` fields). Load is defensive (non-dict / malformed JSON degrades to
empty). Save is non-atomic (plain write).

## Documented Contract Hole

**`remove()` and `_has_whitelist` — CONFIRMED contract (ARCH-84, Option A:
recompute after deletion).** The hole was that `_has_whitelist` is set to
`True` by `add_allow` and recomputed in `_load`, but `remove()` deleted the
rule and saved **without recomputing it** — so removing the last allow rule
left `_has_whitelist == True` even though no allow rule remained, and
`is_allowed()` for every *unlisted* domain silently flipped from `True`
(allow-all) to `False` (deny-all). The architect resolved the open choice in
cycle 288 by confirming **Option A (lossless, symmetric with `_load`)** as the
contract:

- `remove()` recomputes `_has_whitelist = any(r.allowed for r in
  _rules.values())` after `del self._rules[domain]` (the same expression
  `_load` uses), so the flag is always derived from the surviving rule set.
- Removing the **last** allow rule restores the allow-all default: after
  `add_allow("a.com")` then `remove("a.com")`, `is_allowed("unlisted.com")`
  is `True` and `list_rules() == []`.
- Removing **one of many** allow rules keeps the whitelist active: after
  `add_allow("a.com")` + `add_allow("b.com")` then `remove("a.com")`,
  `is_allowed("unlisted.com")` is still `False` and `is_allowed("b.com")` is
  `True`.
- Removing a **block** rule is a no-op for the flag: after
  `add_block("b.com")` then `remove("b.com")`, `is_allowed("unlisted.com")`
  is `True` (a block-only set was never a whitelist).

The `remove()` and class docstrings must state this invariant. The existing
tests (`test_remove_rule`, `test_remove_nonexistent`,
`tests/deep/test_domains_adversarial.py::test_remove_existing`,
`test_remove_missing`) assert only the *removed domain's own* status and must
still pass unchanged; the corrected contract is pinned by the new
`tests/test_domains.py` tests named in ARCH-84
(`test_remove_last_allow_restores_allow_all`,
`test_remove_one_of_many_keeps_whitelist`,
`test_remove_block_keeps_allow_all`), which are the witness that this
corrected contract matches the implemented behavior. (Adjacent behaviors that
are **NOT** holes: `from_dict` non-mapping/unknown-key degradation, the
`max_pages=0`/`>=` boundary, exact-match case sensitivity, and
block-does-not-set-whitelist are all already pinned by
`tests/deep/test_domains_adversarial.py`.)
