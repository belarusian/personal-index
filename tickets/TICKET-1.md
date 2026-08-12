# TICKET-1: Dead CLI modules — 20 separate cli_*.py files never imported

## Evidence

The following `cli_*.py` modules exist in `personal_index/` but are **never imported** by any other source module or test file:

- `cli_clear.py`
- `cli_crawl.py`
- `cli_doctor.py`
- `cli_export.py`
- `cli_extract.py`
- `cli_import.py`
- `cli_interests.py`
- `cli_list.py`
- `cli_merge.py`
- `cli_pipeline.py`
- `cli_remove.py`
- `cli_schedule.py`
- `cli_score.py`
- `cli_search.py`
- `cli_stats.py`
- `cli_status.py`
- `cli_tags.py`
- `cli_top.py`
- `cli_verify.py`
- `cli_watch.py`

Only 3 CLI modules are imported in `cli.py` (lines 1390-1395):
