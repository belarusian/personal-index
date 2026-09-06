# TICKET-475: Timeline.get_summary generic docstring (class-(b) doc-drift)

- File: personal_index/content_timeline/timeline.py
- Method: Timeline.get_summary
- Symptom (class-b doc drift): docstring is the blanket claim "Get a summary of the timeline." while the body returns a dict with exactly the keys total_events, total_entries, content_ids (content_ids is a list of unique content IDs from events).
- Evidence line: `def get_summary` docstring (line ~119) vs return dict construction (lines ~120-124).
- Minimal additive fix: reword the docstring to state the exact keys returned and their meanings; add ONE behavior test pinning the corrected claim (keys present and values match len(events), len(entries), list(content_ids)).
- Status: OPEN
- Issue: #798
