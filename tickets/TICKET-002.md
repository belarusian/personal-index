# TICKET-002: Refactor pipeline_runner.run (107 lines) into stage functions

**File:** `personal_index/pipeline_runner.py`  
**Function:** `PipelineRunner.run` (lines 103–210)  
**Lines:** 107  
**Severity:** Medium

## Evidence

The `run` method performs 6 pipeline stages sequentially in a single method body:

- Lines 110–120: Stage 1 — Crawl (calls `self._crawler.crawl()`)
- Lines 122–135: Stage 2 — Extract (iterates pages, calls `_read_file`)
- Lines 137–150: Stage 3 — Filter (calls `self._filter.should_include()`)
- Lines 152–170: Stage 4 — Score (calls `self._score_page()`)
- Lines 172–190: Stage 5 — Tag (calls `self._auto_tag_page()`)
- Lines 192–210: Stage 6 — Index (calls `self._search_index.add_page()`)

Each stage has its own try/except, progress callback, and stats update — a clear pattern of repeated structure.

## Impact

- Adding a new pipeline stage requires modifying a 107-line method
- Stage-level error handling is duplicated per stage
- Cannot test individual stages in isolation

## Suggestion

Extract each stage into a private method with a common signature:
