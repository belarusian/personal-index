# TICKET-440: get_index_stats blanket docstring does not enumerate guard path or sub-components

Status: RESOLVED (PR #719, commit c857ca5)
Module: personal_index/stats.py
Function: StatsCollector.get_index_stats

## Symptom
The docstring is a blanket "Calculate current index statistics." that does not
enumerate the behavior the body actually performs:
- Guard path: when `self.search_index` is falsy, the method returns an
  all-default `IndexStats` (every field at its dataclass default) without
  touching the index.
- `top_domains` / `top_interests` are capped to the top 10 entries (sorted by
  count descending).
- `oldest_page` / `newest_page` are only set when at least one page has a
  `crawled_at` timestamp; otherwise they remain `None`.

## Evidence
personal_index/stats.py, `get_index_stats` docstring (line ~48):
    """Calculate current index statistics."""
Body: `if not self.search_index: return stats` (guard); `[:10]` caps on
top_domains/top_interests; `if timestamps:` gates oldest/newest.

## Minimal additive fix
Reword the docstring to state the EXACT behavior (guard path + top-10 cap +
conditional oldest/newest). Add ONE pinning test asserting the RETURNED OBJECT
fields: guard path (no search_index -> all defaults, oldest/newest None)
alongside the populated main behavior (top-10 cap, oldest/newest set).

## Issue: #718
