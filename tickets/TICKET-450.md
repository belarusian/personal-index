# TICKET-450: content_webhooks.WebhookManager.mark_failed never schedules a retry

Status: OPEN
Issue: #739
Module: personal_index/content_webhooks.py
Method: WebhookManager.mark_failed

## Symptom
The `mark_failed` docstring claims: "Mark a payload as failed and
**schedule retry if possible**." But the body never schedules any retry:
when `endpoint.should_retry()` is True (retries remain) it does nothing —
it only increments `failure_count` and leaves the payload in `pending`
with no retry time recorded. The payload is only moved to `delivered`
when retries are exhausted. So the "schedule retry" half of the claim is
undelivered: there is no `next_retry_at` field and no code path that
computes a next retry time.

## Evidence
personal_index/content_webhooks.py:
- docstring: "Mark a payload as failed and schedule retry if possible."
- body: `if not endpoint.should_retry():` -> remove from pending, append
  to delivered. The `else` (retries remain) branch is empty — no retry is
  scheduled.
- `WebhookPayload` dataclass has no `next_retry_at` field.
- `WebhookEndpoint` has `retry_delay` (base delay between retries in
  seconds) which is never used.

## Classification
IMPLEMENTABLE. The endpoint already carries `retry_delay` and
`should_retry()`; adding a `next_retry_at` field to `WebhookPayload` and
setting it to `now + retry_delay` when retries remain makes the ORIGINAL
claim true.

## Minimal additive fix
Add `next_retry_at: datetime | None = None` to `WebhookPayload`. In
`mark_failed`, when `endpoint.should_retry()` is True, set
`payload.next_retry_at = now(timezone.utc) + timedelta(seconds=endpoint.retry_delay)`;
when exhausted, set it to None before moving to delivered. Add ONE
pinning test: an endpoint with max_retries=3, dispatch one payload, call
`mark_failed` once (failure_count 1 < 3) and assert the payload STAYS in
pending, is NOT in delivered, and `next_retry_at` is set to a time >= now.
