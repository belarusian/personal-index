# TICKET-256: content_categorizer `_add_matches` mislabels title/meta signal sources as "text"

## File
personal_index/content_categorizer.py

## Symptom
`TopicScore.signal_sources` is meant to report WHERE a keyword signal came from
(text / title / meta_description / url_hint). But `_add_matches` (line 446)
hardcodes `src.append("text")` whenever it records a match. It is called from
the title branch (line 479) and the meta_description branch (line 485), so a
keyword matched in the **title** or **meta_description** is falsely reported as
a "text" source. The `sources` list then contains both the wrong "text" label
and the correct "title"/"meta_description" label.

## Evidence
- Line 446-452: `_add_matches` does `if matches: src.append("text")` (hardcoded).
- Line 479: `self._add_matches(ttm, matched, sources)` in the title branch,
  followed by `sources.append("title")` (line 480).
- Line 485: `self._add_matches(mm, matched, sources)` in the meta branch,
  followed by `sources.append("meta_description")` (line 486).
- The text branch (line 471-476) does NOT use `_add_matches`; it appends
  "text" directly. So `_add_matches` is only ever used for title/meta, and its
  hardcoded "text" is always wrong.

## Minimal additive fix
Parameterize the source label in `_add_matches` (default "text" to preserve the
contract), and pass the correct label at the two call sites:
  - `_add_matches(self, matches, kw, src, source="text")` -> `src.append(source)`
  - title branch: `self._add_matches(ttm, matched, sources, "title")`
  - meta branch: `self._add_matches(mm, matched, sources, "meta_description")`
Add a test asserting a title-only match yields signal_sources == ["title"]
(no spurious "text"), and a meta-only match yields ["meta_description"].

Issue: #341

## Status
OPEN
