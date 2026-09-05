# TICKET-429: content_notifications.NotificationManager.evaluate_event doc-drift

Status: RESOLVED
Merged: 1dbe74f (PR #697)
Issue: #696 CLOSED

## File
personal_index/content_notifications.py

## Symptom
Class-(b) doc-drift: the docstring is a blanket one-liner ("Evaluate an event
against all rules and generate notifications.") that does not enumerate the
sub-components the body actually performs:
- Guard path 1: rules where `rule.matches(event)` is False are skipped
- Guard path 2: rules whose cooldown hasn't elapsed since the last notification
  (`_last_sent[rule.rule_id]`) are skipped
- Side effect: each generated notification is appended to `self.notifications`
- Side effect: `_last_sent[rule.rule_id]` is updated to `now` for each fired rule
- Return: list of generated Notification objects (may be empty)

## Evidence
Line 142: `"""Evaluate an event against all rules and generate notifications.`
Lines 143-147: Args/Returns only mention "event" and "List of generated
notifications" — no mention of cooldown, rule matching, or side effects.

## Minimal additive fix
Reword the docstring to state the exact conditional (rule.matches + cooldown
guard) and the two side effects (self.notifications append, _last_sent update)
plus the return. Add ONE pinning test asserting the RETURNED LIST fields for
both the normal case (matching rule, no cooldown -> notification returned) and
the guard path (non-matching rule -> empty list returned).

## Issue
Issue: #696
