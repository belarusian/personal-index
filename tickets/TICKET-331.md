# TICKET-331 — content_notifications.NotificationManager class docstring over-promises "delivers notifications through configured channels"

- Status: OPEN
- Class: (b) doc/behavior drift
- Module: personal_index/content_notifications.py
- Issue: #500

## Symptom
The `NotificationManager` class docstring (lines 114-118) claims the manager
"Stores rules, evaluates events against rules, and delivers notifications
through configured channels." There is no delivery mechanism anywhere in the
class: no send/dispatch/emit/deliver method, and the `channels` field on
`NotificationRule`/`Notification` is stored but never used to perform
delivery. The class only (a) stores rules (`add_rule`/`remove_rule`),
(b) evaluates events against rules to generate notifications
(`evaluate_event`), and (c) tracks delivery state via a `delivered` flag that
is set externally by the caller (`mark_delivered`/`mark_all_delivered`). The
"delivers notifications through configured channels" capability is an
over-promise.

## Evidence
- `sed -n '113,119p' personal_index/content_notifications.py` shows the class
  docstring ending with "delivers notifications through configured channels."
- `grep -n 'deliver\|send\|dispatch\|emit\|notify\|channel'
  personal_index/content_notifications.py` matches only the docstrings, the
  `channels` field declarations (lines 58, 94), the `delivered`/`delivered_at`
  flag fields (lines 96-97), `to_dict` serialization (lines 107-109), and the
  `mark_delivered`/`mark_all_delivered` state setters (lines 170-187). No
  method performs delivery through a channel.
- `evaluate_event` (lines 138-164) only appends a `Notification` to
  `self.notifications` and returns it; it never dispatches to any channel.
- `mark_delivered` (lines 170-177) merely flips `n.delivered = True` and sets
  `n.delivered_at`; the caller is responsible for the actual delivery.

## Minimal additive fix
Correct the class docstring to describe only the capabilities actually
implemented. Change lines 114-118 from
"Manages notification rules and delivery. / Stores rules, evaluates events
against rules, and delivers notifications through configured channels." to
"Manages notification rules and delivery state. / Stores rules, evaluates
events against rules to generate notifications, and tracks their delivery
state." (the three real behaviors: rule storage, event evaluation, delivery
state tracking).

Add ONE regression test
`TestNotificationManagerDocstring::test_docstring_does_not_promise_channel_delivery`
that asserts "delivers notifications" is absent from
`NotificationManager.__doc__`, so the over-promise cannot silently return.
