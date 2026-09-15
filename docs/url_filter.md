# url_filter — `personal_index.url_filter`

Spec page (matches CURRENT code as of cycle 256).

`url_filter.py` is the URL allow/deny filter. It exposes two public types:
`UrlFilterRule` (a single pattern rule) and `UrlFilter` (the rule set + the
allow/block decision). It performs **no** persistence and **no** network I/O —
it is a pure in-memory matcher. It does **not** own URL parsing/validation —
those live in `personal_index.url_utils` (see `docs/url-utils.md`) and
`personal_index.url_classifier` (see `docs/url-classifier.md`). This page
documents `personal_index.url_filter` (`UrlFilter` / `UrlFilterRule`), which is
**DIFFERENT** from the near-name siblings:

- `personal_index.url_dedup` (`docs/url-dedup.md`) — deduplicates a URL list;
  it does not allow/block by pattern.
- `personal_index.url_utils` (`docs/url-utils.md`) — 22 stateless URL string
  helpers; no rule set, no allow/block decision.
- `personal_index.url_classifier` (`docs/url-classifier.md`) — classifies a URL
  into a category; it does not filter a list.

## `UrlFilterRule` (dataclass, line 11)

Fields (in declaration order): `pattern: str` (line 13),
`is_blacklist: bool = True` (line 14), `description: str = ""` (line 15).

### `matches(url: str) -> bool` (line 17)

Three match strategies, tried in this order; the FIRST that succeeds returns
`True`:

1. **Exact match** (line 20): `self.pattern == url` — the raw pattern string is
   compared byte-for-byte to the URL.
2. **fnmatch wildcards** (line 23): `fnmatch.fnmatch(url, self.pattern)` —
   `*`/`?`/`[...]` glob semantics over the whole URL.
3. **regex** (line 26): only when `self.pattern.startswith("re:")` — the
   pattern is stripped of the `re:` prefix (line 27) and matched with
   `re.search` (line 29), i.e. **substring / unanchored** search, not
   `re.match`. A malformed regex (`re.error`) is **swallowed and returns
   `False`** (lines 30-31) — a documented design constraint pinned by
   `tests/deep/test_url_filter_adversarial.py` (line 59: "re.error must be
   swallowed -> False, not raised").

If none of the three strategies match, `matches` returns `False` (line 32).

**Ordering note (guard path):** the fnmatch check (line 23) runs **before** the
`re:` prefix is even inspected (line 26). A pattern like `re:example` has no
fnmatch wildcard, so `fnmatch(url, "re:example")` is `False` for a normal URL
and the regex branch is reached; but a pattern that is BOTH a valid fnmatch
glob AND starts with `re:` would be decided by fnmatch first. The regex branch
is only consulted when the fnmatch check has already returned `False`.

## `UrlFilter` (class, line 35)

Holds two private lists: `self._blacklist: list[UrlFilterRule]` (line 40) and
`self._whitelist: list[UrlFilterRule]` (line 41). The class docstring (lines
36-40) states the precedence contract: **whitelist rules take precedence over
blacklist rules** — a URL matching any whitelist rule passes; only when no
whitelist rule matches is the blacklist consulted.

### Mutators

- `add_blacklist(pattern, description="")` (line 47): appends a
  `UrlFilterRule(pattern, is_blacklist=True, ...)` to `_blacklist` (line 49).
- `add_whitelist(pattern, description="")` (line 51): appends a
  `UrlFilterRule(pattern, is_blacklist=False, ...)` to `_whitelist` (line 53).
- `clear()` (line 139): clears both lists.
- `clear_blacklist()` (line 144): clears `_blacklist` only.
- `clear_whitelist()` (line 148): clears `_whitelist` only.

### Decision methods

- `is_allowed(url) -> bool` (line 55): scans `_whitelist` first; the first
  whitelist rule whose `matches(url)` is `True` returns `True` (lines 65-67).
  Only when no whitelist rule matches does it return
  `all(not rule.matches(url) for rule in self._blacklist)` (line 69) — i.e.
  allowed iff **no** blacklist rule matches. An empty filter (no rules at all)
  returns `True` (the `all(...)` over an empty list is `True`).
- `is_blocked(url) -> bool` (line 71): `not self.is_allowed(url)` (line 79).
- `filter_urls(urls) -> list[str]` (line 82): returns the URLs for which
  `is_allowed` is `True`, preserving input order (line 91).
- `get_blocked_urls(urls) -> list[str]` (line 93): returns the URLs for which
  `is_blocked` is `True`, preserving input order (line 102).
- `get_matching_rule(url) -> UrlFilterRule | None` (line 104): scans
  `_whitelist` first, then `_blacklist`; returns the **first** rule (in
  insertion order within each list) whose `matches(url)` is `True`, or `None`
  when neither list has a match (lines 121-128). Returns the actual stored
  object (identity, not a copy). Pure accessor — does not mutate either list.

### Counters

- `blacklist_count` (property, line 130): `len(self._blacklist)`.
- `whitelist_count` (property, line 135): `len(self._whitelist)`.

## Contract hole (ARCH-87): `UrlFilterRule.is_blacklist` is never consulted

`is_blacklist` (line 14) is a **public dataclass field** whose name implies it
drives the block/allow decision, but **no filtering logic in the module reads
it**. `grep -rn is_blacklist personal_index/ --include='*.py'` returns exactly
three lines, all **writes**:

    line 14:  is_blacklist: bool = True          # declaration
    line 49:  ...is_blacklist=True, ...          # add_blacklist
    line 53:  ...is_blacklist=False, ...         # add_whitelist

The block/allow decision is made **purely by list membership**: a rule is a
whitelist rule iff it sits in `self._whitelist`, and a blacklist rule iff it
sits in `self._blacklist`. `is_allowed` (lines 65-69) and `get_matching_rule`
(lines 121-128) iterate the two lists and never inspect `rule.is_blacklist`.
So the field is **redundant with list membership** and cannot route a rule:
constructing `UrlFilterRule("*.x.com", is_blacklist=False)` and appending it to
`_blacklist` (bypassing `add_whitelist`) still behaves as a blacklist rule,
because the list — not the field — decides. The `True` default (line 14) is
also **unreachable via the public API**: both `add_blacklist` and
`add_whitelist` pass an explicit `is_blacklist`, so a caller can never observe
the default through the documented surface.

The field is **masked by the tests**: `tests/test_url_filter.py`
(`test_whitelist_returned_when_both_match`, line 144;
`test_blacklist_returned_when_no_whitelist_match`, line 151) assert
`rule.is_blacklist is False` / `is True` on the object returned by
`get_matching_rule`. Those assertions pass because the field is *written*
correctly by the add_* methods — but they do not exercise the field as a
*decision input*, so the suite stays green whether or not the field is ever
read. This is the same "public field does nothing" class as ARCH-86
(`StatsCollector.interest_store`).

**Recommended resolution (a) — remove the dead field:** drop `is_blacklist`
from `UrlFilterRule` (line 14) and the two `is_blacklist=` keyword arguments in
`add_blacklist` (line 49) / `add_whitelist` (line 53). `UrlFilterRule` then has
exactly two fields, `pattern` and `description`. All decision behavior
(`is_allowed` / `is_blocked` / `filter_urls` / `get_blocked_urls` /
`get_matching_rule`) is **exactly as today** — it never read the field, so
nothing about the returned values changes; only the dead public surface goes.
The `UrlFilterRule` docstring and the `get_matching_rule` docstring must state
that block/allow is decided by **list membership** (whitelist list vs
blacklist list), not by a per-rule flag.

Resolution **(b)** — make `is_blacklist` the actual routing key (e.g. a single
`_rules` list where `is_allowed` consults `rule.is_blacklist`) — is the
alternative; it is a behavior change and is NOT recommended because it would
restructure the two-list invariant the existing `tests/test_url_filter.py` and
`tests/deep/test_url_filter_adversarial.py` suites pin. If (b) is chosen, the
ticket must restate the exact new data layout and the pinning tests that
change. **The implementer must not do both.**
