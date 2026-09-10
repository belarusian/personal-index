Status: IMPLEMENTED PR#1243@6ed638c
Kind: ARCH
Author: architect (cycle 183)
Issue: #1058

# ARCH-21: rss — `parse` silently returns an empty `Feed` for non-feed root tags

## Component
`personal_index/rss.py` (home: `docs/content-rss.md`).
One contract hole in the feed parser's dispatch.

## Symptom

`RSSParser.parse(xml_content, feed_url="")` parses the root, strips any
namespace prefix, and dispatches on the bare root tag name: `"rss"` →
`_parse_rss`, `"feed"` → `_parse_atom`. **Any other root tag** (e.g.
`<html>`, `<rdf:RDF>`, `<atom>`, a bare `<item>`) falls through both branches
and returns the empty `Feed(feed_url=feed_url)` — no entries, no title, no
exception, no flag.

A caller cannot distinguish "a valid feed with zero entries" from "this was
not a feed at all". The module already ships `RSSParser.is_feed(xml_content)`
precisely to pre-check, but `parse` neither calls it nor records that the
dispatch fell through, so the two signals are disconnected: a caller who
skips `is_feed` gets a silently-empty `Feed` for HTML and has no way to know.

## Public contract (the fix)

Make the non-feed-root case observable without changing the happy path.
Preferred: `parse` returns a `Feed` whose `entries` is empty **and** whose
`title` is empty, but additionally the module exposes a way to tell the two
apart. Two acceptable shapes (implementer picks one, states it in the
docstring):

- **Option A (flag):** add `Feed.parsed_as_feed: bool = True` (or a
  `Feed.is_valid: bool = True`) set to `False` on the non-feed-root fall-through
  path (and on the empty/parse-error guard paths, which are also "not a
  parsed feed"). `parse` for a real `rss`/`feed` root leaves it `True`.
- **Option B (exception):** `parse` raises a `ValueError` (or a new
  `NotAFeedError`) when the root tag is neither `rss` nor `feed`, while the
  empty-input and parse-error guard paths still return an empty `Feed`.

Whichever is chosen, the `parse` docstring must state the exact dispatch
condition and the non-feed-root behavior, and `docs/content-rss.md` must
reflect it (drop contract hole 1, renumber the rest).

## Acceptance criteria
- For XML whose root tag is neither `rss` nor `feed`, the caller can
  distinguish the result from a valid zero-entry feed (via the flag or the
  exception, per the chosen option).
- `parse` for a real RSS 2.0 or Atom feed is unchanged (same `Feed` fields,
  same entries).
- The empty-input and parse-error guard paths still return an empty `Feed`
  (no new exception on those paths under Option B).
- `docs/content-rss.md` contract hole 1 is removed and the remaining holes
  renumbered; the `parse` dispatch is documented. Shipped in the SAME PR.

## Pinning tests to add (in `tests/test_rss.py`)
- **Non-feed root (the hole):** one test that parses a minimal non-feed XML
  (e.g. `<html><body>x</body></html>`) and asserts the chosen signal (flag is
  `False` / exception raised) — alongside a real zero-entry `<rss><channel/>`
  feed that asserts the signal is `True` (no exception), so one pair pins both
  the fall-through path and the valid-empty path.
- **Guard paths unchanged:** empty-string input and a malformed-XML input both
  still return an empty `Feed` (no exception) under the chosen option.

## Docs update (SAME PR)
`docs/content-rss.md`:
- In `RSSParser.parse`, state the exact dispatch condition and the
  non-feed-root behavior (flag or exception).
- Remove contract hole 1 (silent empty feed) and renumber holes 2–4 to 1–3.
