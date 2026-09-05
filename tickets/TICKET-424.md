# TICKET-424 — content_filter.ContentFilter.get_filter_reasons blanket docstring

- Status: OPEN
- Class: (b) doc-drift (over-promise / non-enumerating docstring)
- File: personal_index/content_filter.py
- Function: ContentFilter.get_filter_reasons (line ~54)

## Symptom
Docstring is a blanket one-liner: "Get list of reasons why a page was filtered
out." It does not enumerate the sub-components the body actually performs, so a
reader cannot tell which checks run, in what order, or which are conditional on
config / interest_store.

## Evidence (line)
- personal_index/content_filter.py:55  `"""Get list of reasons why a page was filtered out."""`
- Body performs 8 checks in order:
  1. content length < config.min_content_length
  2. content length > config.max_content_length
  3. title length < config.min_title_length
  4. _is_blocked_domain(page.url)
  5. _matches_blocked_patterns(page)
  6. _compiled_required and not _matches_required_patterns(page)
  7. config.require_interest_match and interest_store and not _matches_interests(page)
  8. interest_store and config.min_relevance_score > 0 and total_score < min_relevance_score

## Minimal additive fix
Reword the docstring to enumerate the 8 checks (with their exact conditionals
and the reason strings they append), and state the return value (list[str],
empty when the page passes every check). Add ONE pinning test asserting the
RETURNED list fields for the normal case (multiple reasons, in order) AND the
guard path (a page that passes every check -> empty list).

## Issue
Issue: #686
