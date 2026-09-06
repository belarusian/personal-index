# TICKET-466

## File
`personal_index/content_timeline/timeline.py` — `Timeline.add_entry` (line 26)

## Symptom
Class-(b) doc-drift: the docstring is the generic one-liner
`"""Add a TimelineEntry to the timeline."""` which enumerates none of the
behavior the body actually performs.

## Evidence (line)
- L36: `"""Add a TimelineEntry to the timeline."""` (generic, no enumeration)
- L37-45: builds a `TimelineEntry` with `timestamp or datetime.now(timezone.utc)`
  (default timestamp) and `metadata or {}` (default metadata) — not documented
- L46: `self.entries.append(entry)` (append not documented)
- L47: `self.entries.sort(key=lambda e: e.timestamp, reverse=True)` (reverse /
  newest-first sort not documented)
- L48: `return entry` (return not documented)

## Minimal additive fix
Reword the `add_entry` docstring to enumerate, in order:
(1) build a `TimelineEntry` from the given fields, defaulting `timestamp` to
`datetime.now(timezone.utc)` when omitted and `metadata` to `{}` when omitted;
(2) append the entry to `self.entries`;
(3) re-sort `self.entries` in reverse (newest-first) order by timestamp;
(4) return the created entry.
NO behavior change. Add pinning tests for the defaults, the reverse sort, and
the return value.

Issue: #773

## Status
OPEN
