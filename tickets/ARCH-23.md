# ARCH-23: crawler/robots — RobotsParser.parse never populates _policies (dead branch) + empty-Disallow disallows all

- **Status:** OPEN
- **Component:** `personal_index/crawler/robots.py` (the LIVE robots module;
  `personal_index/robots_parser.py` is a dead duplicate — see docs/content-robots.md
  contract hole 1, tracked separately).
- **Issue:** #1062

## Symptom
Two genuine contract holes in the live `crawler/robots.py`:

1. `RobotsParser.parse(text, base_url)` stores only `self._rules =
   policy.rules` and **never** stores the policy in `self._policies`. So
   `RobotsParser.can_fetch()`'s `if domain in self._policies:` branch is
   unreachable dead code, and `parse()` silently discards `domain`,
   `crawl_delay`, and `sitemap_urls`.
2. A `Disallow:` / `Allow:` line with an **empty value** still appends
   `RobotsRule(agent, allowed, "")`. `""` matches every path via
   `path.startswith("")`, so a bare `Disallow:` silently disallows the whole
   site.

## Evidence
- `personal_index/crawler/robots.py:130` — `parse()` body:
  `policy = parse_robots_txt(text, base_url); self._rules = policy.rules`
  (no `self._policies[...] = policy`).
- `personal_index/crawler/robots.py:140` — `can_fetch()`:
  `if domain in self._policies: return self._policies[domain].can_fetch(...)`
  (unreachable; `self._policies` is only ever `= {}` in `__init__`).
- `personal_index/crawler/robots.py:98-110` — `disallow`/`allow` dispatch
  guards on `and current_agent` only, not `and value`, so an empty value
  appends a `pattern=""` rule.

## Public contract (target state)
- `RobotsParser.parse(text, base_url) -> None` MUST store the parsed policy
  keyed by domain: `self._policies[policy.domain] = policy` (keep
  `self._rules = policy.rules` for backward compatibility). After `parse`,
  `can_fetch(url)` for a URL whose netloc equals the parsed domain MUST take
  the per-domain branch and return the same boolean as
  `policy.can_fetch(url, user_agent)`.
- `parse_robots_txt` MUST drop `disallow`/`allow` lines whose value is empty
  (guard `and value`), so a bare `Disallow:` produces no rule and does not
  disallow the site.

## Acceptance criteria
1. After `RobotsParser().parse("User-agent: *\nDisallow: /private\n",
   "https://example.com")`, `can_fetch("https://example.com/private/x")` is
   `False` and the per-domain branch is exercised (domain present in the
   parser's policy store).
2. `parse_robots_txt("User-agent: *\nDisallow:\n", "https://example.com")`
   → `can_fetch("https://example.com/anything")` is `True` (empty value
   dropped), while a normal `Disallow: /private` still returns `False` for
   `/private/x`.
3. Existing `tests/test_robots.py` and `tests/test_sim102_nested_if.py` stay
   green (no behavior change for non-empty patterns).

## Pinning tests to add
- `test_robots_parser_parse_populates_policies` (normal + per-domain branch).
- `test_empty_disallow_does_not_disallow_all` (guard path: empty value,
  alongside a normal `Disallow: /private` case).

## Docs
`docs/content-robots.md` (this cycle) documents both holes; the implementer
keeps the page true when fixing (update the "Contract holes" section to
RESOLVED and the `RobotsParser.parse` / `parse_robots_txt` behavior lines).
