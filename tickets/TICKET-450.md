# TICKET-450

- Module: personal_index/content_webhooks.py
- Method: WebhookManager.mark_failed
- Issue: #739
- Status: RESOLVED

## Symptom
`mark_failed` increments `attempts`/`last_error`/`failure_count` and, when
`not endpoint.should_retry()`, moves the payload to `delivered`. But when
retries remain (`endpoint.should_retry()` is True) it does NOTHING — no retry
time is recorded. `WebhookPayload` has no `next_retry_at` field at all, so the
manager can never tell when a failed payload should be retried.

## Evidence
- `WebhookPayload` dataclass (line 72) has no `next_retry_at` field.
- `mark_failed` (line 202): the `if not endpoint.should_retry():` branch moves
  to delivered; the retries-remain path is empty (no retry scheduling).
- `WebhookEndpoint` already has `retry_delay: float = 1.0` (line 60) and
  `should_retry()` (line 66) — the inputs exist, the behavior does not.

## Minimal additive fix
- Add `next_retry_at: datetime | None = None` to `WebhookPayload` (+ docstring
  Attributes entry).
- In `mark_failed`, when `endpoint.should_retry()` is True set
  `payload.next_retry_at = now(timezone.utc) + timedelta(seconds=endpoint.retry_delay)`;
  when exhausted (moving to delivered) set `payload.next_retry_at = None`.
- Import `timedelta` from `datetime`.
- Add ONE pinning test: max_retries=3, dispatch, mark_failed once (failure_count
  1 < 3) -> payload stays pending, not delivered, `next_retry_at` >= now.
