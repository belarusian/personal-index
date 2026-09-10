# Content Robots (spec)

`personal_index.crawler.robots` — the robots.txt parsing component of the
crawl stage. Given a raw robots.txt string (and an optional base URL), it
parses `user-agent` / `disallow` / `allow` / `crawl-delay` / `sitemap`
directives into a structured `RobotsPolicy` and answers "may this user agent
fetch this URL?" with longest-pattern-wins matching. It does **no network
I/O** — fetching the robots.txt bytes is the crawler's job; this module only
parses and matches.

The module exports five names: `RobotsRule`, `RobotsPolicy`,
`parse_robots_txt`, `is_allowed`, `RobotsParser`.

> **Two robots modules exist.** `personal_index.crawler.robots` (this page) is
> the LIVE one — it is what `tests/test_robots.py` and
> `tests/test_sim102_nested_if.py` import. `personal_index.robots_parser` is a
> near-duplicate that is **never imported anywhere** (dead module, see
> contract hole 1). Do not confuse the two: they differ in default user agent,
> wildcard handling, and pattern-matching semantics.

## Public API

### `RobotsRule` (dataclass)
A single robots.txt rule. Fields, in order:
- `user_agent: str` — the `User-agent:` value the rule applies to (`"*"` for
  the wildcard block).
- `allowed: bool` — `False` for a `Disallow:` line, `True` for an `Allow:`
  line.
- `pattern: str` — the path pattern (may contain `*` and a trailing `$`).

### `RobotsPolicy` (dataclass)
A parsed robots.txt policy for one domain. Fields, in order:
- `domain: str` — the `netloc` of `base_url` (or `""` when `base_url` is
  empty / has no netloc).
- `rules: list[RobotsRule] = []` — every parsed `Allow`/`Disallow` rule, in
  file order.
- `crawl_delay: float = 0.0` — the last `Crawl-delay:` value that parsed as a
  float; stays `0.0` when absent or non-numeric (a `ValueError` is
  suppressed, not raised).
- `sitemap_urls: list[str] = []` — every `Sitemap:` value, in file order.

#### `RobotsPolicy.can_fetch(url: str, user_agent: str = "*") -> bool`
Decides whether `user_agent` may fetch `url`. Behavior, in order:
1. `path = urlparse(url).path or "/"` (query/fragment are ignored; an empty
   path becomes `"/"`).
2. **Applicable rules** = every rule where `rule.user_agent == "*"` **OR**
   `rule.user_agent.lower() == user_agent.lower()`. Note this is a
   *union* — wildcard and specific-agent rules are both considered together
   (unlike the dead `robots_parser` module, which prefers specific over
   wildcard).
3. If no rules apply, **default-allow** → `True`.
4. Otherwise the **longest matching pattern wins**: among applicable rules
   whose pattern matches `path` (via `_matches`), the one with the greatest
   `len(pattern.rstrip("/"))` is returned; its `allowed` flag is the result.
   If no applicable pattern matches, **default-allow** → `True`.

#### `RobotsPolicy._matches(path: str, pattern: str) -> bool` (static)
Pattern matcher. Behavior, in order:
- `pattern == "*"` → `True` (matches everything).
- `pattern` ends with `"$"` → strip the `$`, then
  `fnmatch.fnmatch(path, pattern) or path == pattern` (anchored, case-
  insensitive on POSIX via `fnmatch`).
- `pattern` contains `*` → `fnmatch.fnmatch(path, pattern)`.
- otherwise → `path.startswith(pattern)` (plain prefix; note this is a
  **substring-prefix** match, not a path-segment match — `"/a"` matches
  `"/abc"`).

### `parse_robots_txt(text: str, base_url: str = "") -> RobotsPolicy`
Parses a robots.txt string into a `RobotsPolicy`. Behavior:
- `domain = urlparse(base_url).netloc or ""`.
- Iterates `text.splitlines()`; each line is `strip()`-ed.
- **Skipped lines**: empty lines, lines starting with `#`, and lines with no
  `":"` (a `User-agent` line with no value is dropped, not an error).
- `key` is `split(":", 1)` then `strip().lower()`; `value` is `strip()`-ed.
  Dispatch:
  - `user-agent` → sets the current agent (does **not** emit a rule).
  - `disallow` (and a current agent set) → appends `RobotsRule(agent, False, value)`.
  - `allow` (and a current agent set) → appends `RobotsRule(agent, True, value)`.
  - `crawl-delay` → `policy.crawl_delay = float(value)` under
    `suppress(ValueError)` (non-numeric values are ignored, not raised).
  - `sitemap` → appends `value` to `policy.sitemap_urls`.
- **Guard inputs**: `disallow`/`allow` with an **empty value** are dropped
  (the `and current_agent` guard is on the agent, but an empty `value` still
  appends a rule with `pattern=""` — see contract hole 3); a `disallow`/
  `allow` line appearing **before any `user-agent`** line is dropped
  (`current_agent` is still `None`).

### `is_allowed(url: str, policy: RobotsPolicy) -> bool`
Thin wrapper: `return policy.can_fetch(url)` — note it does **not** accept a
`user_agent` argument, so it always uses the default `user_agent="*"`.

### `RobotsParser` (class)
A stateful wrapper that keeps parsed rules across calls.
- `__init__` → `self._rules: list[RobotsRule] = []`,
  `self._policies: dict[str, RobotsPolicy] = {}`.
- `parse(text: str, base_url: str = "") -> None` → calls
  `parse_robots_txt(text, base_url)` and stores **only**
  `self._rules = policy.rules`. It does **not** store the policy in
  `self._policies` and does **not** retain `domain` / `crawl_delay` /
  `sitemap_urls` (see contract hole 2).
- `can_fetch(url: str, user_agent: str = "*") -> bool` → if
  `urlparse(url).netloc` is a key in `self._policies`, delegates to that
  policy's `can_fetch`; otherwise re-derives the decision from `self._rules`
  using the same applicable-rules + longest-pattern-wins logic as
  `RobotsPolicy.can_fetch` (via `RobotsPolicy._matches`).

## Contract holes

1. **Dead duplicate module** — `personal_index.robots_parser` is a second
   `RobotsRule`/`RobotsPolicy`/`parse_robots_txt`/`is_allowed` set that is
   never imported by any module or test. It diverges from the live
   `crawler/robots` in three ways: default `user_agent="personal-index"`
   (vs `"*"`), specific-agent-preferred-over-wildcard rule selection (vs
   union), and a regex-based `*` matcher (vs `fnmatch`). Fix shape: delete
   `robots_parser.py` (or, if it is intended to be the canonical one, rewire
   the imports and tests to it and delete `crawler/robots.py`).

2. ~~**`RobotsParser.parse` never populates `self._policies`**~~ — **RESOLVED** (ARCH-23, cycle 227).
   `parse()` now stores `self._policies[policy.domain] = policy` (and keeps
   `self._rules` for backward compat), so `can_fetch()`'s per-domain branch
   is live and `domain`, `crawl_delay`, and `sitemap_urls` are preserved.

3. ~~**Empty-value `disallow`/`allow` appends a `pattern=""` rule**~~ — **RESOLVED** (ARCH-23, cycle 227).
   `parse_robots_txt` now guards on `and value` for both `disallow` and
   `allow`, so a bare `Disallow:` (empty value) produces no rule and does
   not disallow the site.

## Pinning tests to add (implementer)
- `test_robots_parser_parse_populates_policies` — after
  `RobotsParser().parse("User-agent: *\nDisallow: /private\n",
  "https://example.com")`, assert `can_fetch("https://example.com/private/x")
  is False` **and** that the per-domain path is exercised (e.g. the domain is
  present in the parser's policy store, or the dead branch is removed).
- `test_empty_disallow_does_not_disallow_all` — `parse_robots_txt(
  "User-agent: *\nDisallow:\n", "https://example.com")` →
  `can_fetch("https://example.com/anything") is True` (guard path: empty
  value dropped), alongside a normal `Disallow: /private` case that returns
  `False`.
