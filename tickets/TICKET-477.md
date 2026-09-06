# TICKET-477: TimelineView.render else branch uses timeline.entries instead of timeline.events

## Symptom
TimelineView.render docstring claims it dispatches on mode to select candidate events from timeline.get_events_for_day/week/month which return TimelineEvent objects. The else branch (for unknown mode) uses timeline.entries which are TimelineEntry objects, inconsistent with documented behavior.

## Evidence
File: personal_index/content_timeline/timeline_view.py, line 95-96
else:
    entries = timeline.entries

Docstring (line 70-88) describes dispatch to get_events_for_day/week/month which return TimelineEvent objects, but else branch uses timeline.entries (TimelineEntry objects).

## Minimal Additive Fix
Change else branch to use timeline.events instead of timeline.entries to be consistent with documented behavior.

## Pinning Test
Add test verifying render with unknown mode uses events not entries.

- Status: RESOLVED (PR #803, issue #804 closed, merge 62c6b00)
- Issue: #804
