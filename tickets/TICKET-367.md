# TICKET-367: content_notifications module docstring "delivery" over-promise

Status: OPEN
Issue: #572
Module: personal_index/content_notifications.py
Class: (b) doc-drift (docstring over-promise)

## Triage note
Prior (timed-out) pass opened this ticket against annotation.py. Re-verified:
the `AnnotationStore` CLASS docstring is "Stores and manages annotations."
(accurate, names no data source), and project precedent (TICKET-366 fixed only
the content_health CLASS docstring, leaving its module docstring) shows a module
docstring naming the domain is acceptable. annotation.py FAILS the class-(b)
cross-check (step 1 targets the class docstring). Rejected; ticket repurposed to
the pre-picked module's genuine drift.

## Symptom
The `content_notifications.py` module docstring (line 3) reads:
    "Manages notification rules, triggers, and delivery for
    content-related events such as new bookmarks, score changes,
    and crawl results."
The word "delivery" names a capability the code never performs: the module
never dispatches a notification to any channel.

## Evidence
- `NotificationChannel` (line 31) is a bare Enum; WEBHOOK/EMAIL are labels only.
- `channels` is only stored/copied (NotificationRule.channels,
  Notification.channels, _create_notification copies rule.channels) — never used
  to send. grep for send/dispatch/deliver/notify/emit/.send(/requests/urlopen/
  smtp/webhook/email in the module returns ONLY the two enum labels.
- `mark_delivered` (line 170) / `mark_all_delivered` (line 179) only set
  `n.delivered = True` and `n.delivered_at` — they track delivery STATE, they do
  not deliver.
- `NotificationManager` CLASS docstring is already accurate ("tracks their
  delivery state"); only the MODULE docstring over-promises "delivery".

## Minimal additive fix
Reword the module docstring to state the exact mechanism the code performs:
    "Manages notification rules, evaluates events to generate notifications,
    and tracks their delivery state for content-related events such as new
    bookmarks, score changes, and crawl results.

    Notifications are recorded and their delivered flag toggled by
    mark_delivered/mark_all_delivered; no channel dispatch is performed."
Add ONE behavior test pinning the corrected claim against the returned object:
a fresh NotificationManager holds no notifications (get_undelivered() == [])
AND evaluate_event returns exactly the generated notifications whose delivered
flag is False (witnesses record + state-tracking, not delivery).
