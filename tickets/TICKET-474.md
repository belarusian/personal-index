# TICKET-474: pipeline_orchestrator docstring over-promises "extract" and "search" stages

## File
personal_index/pipeline_orchestrator.py

## Symptom
Module docstring (line 4) claims the pipeline is "crawl → extract → filter → score → tag → index → search".
Class docstring (line 57) claims "crawl → extract → filter → score → tag → index".

The actual `run()` method performs: crawl → filter → score → tag → index.
There is no "extract" stage (pages are crawled and then filtered directly).
"search" is a separate method (`search()`), not a pipeline stage in `run()`.

## Evidence
- Line 4: `crawl → extract → filter → score → tag → index → search`
- Line 57: `crawl → extract → filter → score → tag → index`
- `_execute_stages` (line 221): runs filter → score → tag → index only
- `run()` (line 236): crawl then `_execute_stages` (no extract, no search)

## Fix
Reword module docstring to: "crawl → filter → score → tag → index (search is a separate method)".
Reword class docstring to: "crawl → filter → score → tag → index".
Add one behavior test pinning that `run()` does NOT include an "extract" stage
(stats.pages_extracted equals pages_crawled, confirming no separate extraction step).

## Status
OPEN
Issue: #794
