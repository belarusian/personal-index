# TICKET-510: url_dedup.py seen_count placeholder docstring under-describes behavior

Status: RESOLVED

## File
personal_index/url_dedup.py

## Symptom
`URLDeduplicator.seen_count` (line ~30) carries the placeholder docstring
`"""Seen_count."""`. It does not state the actual contract: a read-only
property returning `len(self._seen_urls)` (int); entries are added only for
non-duplicate URLs via `add_url`; the property does not mutate state.

## Evidence