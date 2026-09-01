# TICKET-245: tracker reconciliation - stale tickets 238-242 vs 0 open gh issues

## File
tickets/TICKET-238.md ... TICKET-242.md

## Symptom
Trackers disagree: 0 open gh issues, 235 closed, but 156 ticket files exist with no
status markers. Several high-numbered tickets describe work already merged.

## Evidence (measured, cycle 1)
- TICKET-240/241/242 (cli.py helper extraction): helpers _expand_import_files,
  _print_pipeline_stats, _print_index_stats, _compute_storage_bytes, _format_stats_text
  all PRESENT in personal_index/cli.py (lines 601-781). Already done (cycles 24-27).
- TICKET-238/239 (coverage for content_versioning / export_markdown): test files are
  now 205 and 170 lines (tickets claimed 7). Already done.
- No ticket carries a Status: line, so nothing is marked resolved.

## Minimal additive fix
Mark tickets 238-242 as RESOLVED (verified against code) so the ticket dir reflects
reality; do NOT re-ticket them. This is reconciliation, not new build work.

## Issue: #323 (gh)

## Status: RESOLVED (merged to main, cycle 1)
