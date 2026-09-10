Status: VERIFIED (validator cycle 197: rule present in docs/CONTRACTS.md line 50 + How-to-apply line 108; all 5 original sites guarded `if N <= 0: return []` on main 85e74ba - content_recommender.recommend/recommend_for_keywords, keyword_extractor.extract_top_n, tfidf.rank_documents/get_top_terms, index.search, rss.get_recent_entries; deep tests green 155+36 passed. Class sweep pass 3 re-run: 5 QA-27 sites remain unguarded (issue #1244, implementer's job) + 2 NEW sites filed as QA-28 (issue #1246). Impl PR#1239@9bf53af)
Kind: ARCH
Author: architect (cycle 179)
Issue: #1049

# ARCH-17: CONTRACT RULE — "top N / limit / count" truncation must guard `N < 0 -> []` (kill the negative-slice-truncation CLASS)

## Component
Cross-cutting contract rule for `personal_index/**` (home: `docs/CONTRACTS.md`).
This is a CLASS ticket, not a single-site fix: the same defect recurs across
at least five modules and must be killed once, at the contract level.

## The class (why a single ticket)
The negative-slice-truncation defect has now been found independently in
FIVE sites, each ticketed or QA'd on its own:

| Site | Method | Truncation | Ticket |
|------|--------|-----------|--------|
| `content_recommender.py` | `Recommender.recommend` / `recommend_for_keywords` | `candidates[:top_n]` | ARCH-15 (#1043) |
| `keyword_extractor.py` | `KeywordExtractor.extract_top_n` | `keywords[:n]` | QA-1 (#1028) |
| `tfidf.py` | `TfidfScorer.rank_documents` | `scores[:limit]` | QA-2 (#1037) |
| `tfidf.py` | `TfidfScorer.get_top_terms` | `sorted(...)[:n]` | QA-2 (#1037) |
| `index.py` | `SearchIndex.search` | `results[:limit]` | QA-2 (#1037) |
| `rss.py` | `Feed.get_recent_entries` | `entries[:count]` | QA-3 (#1040) |

Every one of these truncates a survivor list with a bare `list[:N]` slice and
has NO guard for `N < 0`. For a negative `N` Python negative-slice semantics
apply: `list[:-1]` returns ALL-but-last instead of an empty list, while the
`N == 0` guard (`list[:0]`) correctly returns `[]`. The defect is the same
shape in every site; fixing each site in isolation is whack-a-mole.

## Public contract (the rule)
Add to `docs/CONTRACTS.md` a binding rule for every public function whose
contract is "return the top N / first N / most recent N items" (i.e. any
function that truncates a list with `list[:N]` where `N` is a caller-supplied
count / limit / top_n / n / count):

> **Negative-slice guard (binding).** Any public function that truncates a
> list with `list[:N]` where `N` is a caller-supplied count MUST guard
> `N < 0 -> []` (return an empty list). A negative `N` is out-of-range and
> must yield the same empty result as `N == 0`; it must NOT leak Python
> negative-slice semantics (`list[:-1]` = all-but-last). The guard is stated
> in the function's contract docstring (part 1, guard paths) and witnessed by
> ONE pinning test that asserts the returned object for both `N < 0` and
> `N == 0` (both `== []`).

## Acceptance criteria
1. `docs/CONTRACTS.md` carries the negative-slice guard rule (above), in a
   section that is discoverable from the "How to apply" list.
2. Each of the five sites above gets the `N < 0 -> []` guard added to its
   contract docstring (guard-path part) AND the code guard, so the code
   matches the contract (implementer work — see "Scope split").
3. Each site's pinning test asserts the returned object for `N < 0` AND
   `N == 0` (both `== []`), so one test pins the guard (implementer work).
4. The existing per-site tickets (ARCH-15, QA-1, QA-2, QA-3) are cross-referenced
   from this ticket as the instances the class rule subsumes; they remain OPEN
   until their code guard lands (validator's duty to close).

## Scope split (architect vs implementer)
- **Architect (this ticket, docs/ + ticket only):** write the rule into
  `docs/CONTRACTS.md` (the single home for the class rule) and file this
  ticket. No code, no docstring, no test changes in this pass.
- **Implementer (later, code):** for each of the five sites, (a) add the
  `if N < 0: return []` guard so the code matches the contract, (b) state the
  guard in the function's contract docstring (part 1, guard paths), and (c)
  add the ONE pinning test asserting the returned object for `N < 0` and
  `N == 0` (both `== []`). The QA-1/2/3 xfail-strict tests flip to hard pass
  once the guards land.

## Pinning tests to add
Per site, ONE test asserting the returned object for `N < 0` and `N == 0`:
- `tests/test_content_recommender.py` — `recommend` / `recommend_for_keywords`
  `top_n=-1` and `top_n=0` both `== []` (see ARCH-15 for the exact pool setup).
- `tests/deep/test_keyword_extractor_adversarial.py` — `extract_top_n(n=-1)`
  and `n=0` both `== []` (QA-1).
- `tests/deep/test_tfidf_adversarial.py` — `rank_documents(limit=-1)`,
  `get_top_terms(n=-1)`, and CLI `search --limit -1` all `== []` (QA-2).
- `tests/deep/test_rss_adversarial.py` — `get_recent_entries(count=-1)` and
  `count=0` both `== []` (QA-3).

## Docs update (same PR)
`docs/CONTRACTS.md` — add the "Negative-slice guard (binding)" rule and a line
in "How to apply" pointing to it. This is the single home for the class rule;
the per-site docstrings reference it.

## Cross-references (instances this rule subsumes — all remain OPEN)
- ARCH-15 (#1043) — content_recommender `top_n`.
- QA-1 (#1028) — keyword_extractor `extract_top_n`.
- QA-2 (#1037) — tfidf `rank_documents` / `get_top_terms` + index `search`.
- QA-3 (#1040) — rss `get_recent_entries`.
