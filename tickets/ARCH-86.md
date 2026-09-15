# ARCH-86: `StatsCollector.interest_store` is a public field that is never read, and `CrawlStats` is a public type that is never produced — a "public field does nothing" contract hole

Status: OPEN
Component: `personal_index/stats.py` — `StatsCollector.interest_store` (line 44); `CrawlStats` (line 31); the interest-derived stats `pages_with_interests` (line 80) and `top_interests` (lines 85-88) which are computed from `page.matched_interests` (line 120), not from the store
Umbrella: ARCH-2 (#983)
Issue: #1460
Docs: `docs/stats.md` (Contract Hole, ARCH-86)

## Problem
`StatsCollector` is a `@dataclass` with two public fields:

    interest_store: InterestStore | None = None   # line 44
    search_index:   SearchIndex   | None = None

`interest_store` is accepted in the constructor but is **never read anywhere
in the module** — `grep -c interest_store personal_index/stats.py` returns
exactly 1 (the declaration on line 44). Every interest-derived stat is
computed from the pages themselves, not from the store:

    for interest_name in page.matched_interests:   # line 120
        ...
        pages_with_interests += 1                  # line 124

and `top_interests` (lines 85-88) is built from the same per-page
`matched_interests` counts. So passing a **populated** `InterestStore` has
**zero effect** on any returned stat: `pages_with_interests` and
`top_interests` are identical whether the store is empty or full, because the
collector never consults it. The field's presence implies the collector can
draw interest statistics from the store, but the implementation sources all
interest data from `CrawledPage.matched_interests`.

The sibling dead type is `CrawlStats` (line 31): it is a public `@dataclass`
but is **never produced by any method** — `get_index_stats` returns only
`IndexStats`, and no other method returns a `CrawlStats`. It is imported by
`tests/test_stats.py` (line 10) but never instantiated by the module.

The hole is **masked by the test fixture**: `tests/test_stats.py::interest_store`
(lines 14-17) builds a store populated with a `"Py"` keyword interest and the
`collector` fixture (lines 26-29) passes it in. Because the field is dead, the
tests pass whether or not the store is populated — the populated fixture
masks the dead field rather than exercising it.

This is the same "public field does nothing" class as the dead-type findings
elsewhere (e.g. `ExportStats` in `docs/content-exporter.md`, "dead type — never
returned"): a public surface that implies a capability the implementation does
not provide.

## Public contract (recommended)
Pick **ONE** resolution and state it as the public contract. The recommended
resolution is **(a) remove the dead surface**:

- Remove the `interest_store` field from `StatsCollector` (line 44) and the
  `InterestStore` import it pulls in. `StatsCollector` then has exactly one
  field, `search_index`, and its constructor is `StatsCollector(search_index=...)`.
- Remove the `CrawlStats` dataclass (line 31) — it is never produced.
- `get_index_stats` behavior is **exactly as today**: it still returns
  `IndexStats` computed from `search_index` and the pages' `matched_interests`.
  Nothing about the returned values changes; only the dead public surface goes.
- The `StatsCollector` docstring must state that interest statistics are
  derived from `CrawledPage.matched_interests` (the pages), not from an
  `InterestStore` — so the reader is not led to believe the store is consulted.

Resolution **(b)** — wire the collector to actually consult the
`InterestStore` (e.g. source `pages_with_interests` / `top_interests` from the
store's enabled interests) — is the alternative; it is a behavior change and
is NOT recommended because it would change the returned values that the
existing `TestGetIndexStatsDocPinning` suite pins. If (b) is chosen instead,
the ticket must restate the exact new computation and the pinning tests that
change. **The implementer must not do both.**

## Acceptance criteria
1. After resolution (a): `StatsCollector` has no `interest_store` field;
   constructing it with `interest_store=...` raises `TypeError` (unexpected
   keyword) — the dead surface is gone.
2. `CrawlStats` is no longer importable from `personal_index.stats` (removed).
3. `get_index_stats()` returns the **same** `IndexStats` values as today for
   the same `search_index` (all existing `TestGetIndexStatsDocPinning` and
   `tests/test_stats.py` assertions on returned values stay green).
4. The falsy-`search_index` guard path still returns all-default `IndexStats`
   (existing `test_guard_path_returns_all_defaults` / `test_no_search_index`
   stay green, updated to the new constructor signature).
5. The `docs/stats.md` "Contract Hole" section is updated to reflect the
   resolved contract (dead surface removed) in the SAME PR.

## Pinning tests to add (tests/test_stats.py)
- **Dead-field-removed pin (the hole):** assert `StatsCollector` no longer
  accepts `interest_store` — `inspect.signature(StatsCollector)` has no
  `interest_store` parameter, and `StatsCollector(interest_store=store)`
  raises `TypeError`. Pins the corrected contract against the actual class,
  not the docstring.
- **CrawlStats-removed pin (guard path):** assert `CrawlStats` is not an
  attribute of `personal_index.stats` (`not hasattr(stats, "CrawlStats")`).
- **Returned-values-unchanged pin:** the existing `get_index_stats` value
  assertions (total_pages / unique_domains / avg_content_length /
  pages_with_interests / top_interests) stay green against the same
  `search_index` — pins that removing the dead surface did not change any
  returned stat.

## Docs (SAME PR)
`docs/stats.md` (new, spec) + the `stats.md` index entry in docs/README.md
ship in the same PR as this ticket.
