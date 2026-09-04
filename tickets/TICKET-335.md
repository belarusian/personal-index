# TICKET-335: content_webhooks.mark_failed docstring over-promises retry scheduling

Status: OPEN
Module: personal_index/content_webhooks.py
Class: (b) docstring over-promises behavior the code does not do

## Symptom
`WebhookManager.mark_failed(self, payload_id, error)` docstring reads:
    """Mark a payload as failed and schedule retry if possible."""
The body does NOT schedule any retry. It only:
  1. payload.attempts += 1
  2. payload.last_error = error
  3. endpoint.failure_count += 1
  4. if not endpoint.should_retry(): remove payload from self.pending and
     append to self.delivered.
There is no re-queue, no delayed re-dispatch, no retry timer anywhere in the
module. `should_retry()` is only a threshold check (failure_count < max_retries).
So "schedule retry if possible" is an over-promise.

## Evidence
personal_index/content_webhooks.py:202  (docstring line)
personal_index/content_webhooks.py:203-215 (body: no retry scheduling)
personal_index/content_webhooks.py:67-68  (should_retry = threshold only)

## Minimal additive fix
Reword the docstring to what the code actually does:
    """Mark a payload as failed; drop it to delivered once retries are exhausted."""
Do NOT add retry-scheduling behavior (behavior change, out of scope).

## Regression test
Assert via inspect.getsource that the phrase "schedule retry" is absent from
mark_failed, and that mark_failed moves a payload to delivered when
failure_count reaches max_retries (behavior unchanged).

Issue: #508
