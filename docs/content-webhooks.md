# content_webhooks — spec

`personal_index.content_webhooks`: webhook registration, dispatch, signing, and
retry bookkeeping for content events. **Passive manager** — it creates and
tracks payloads in memory; it performs NO HTTP delivery itself (the caller
delivers `get_payload_json(payload)` and reports back via `mark_delivered` /
`mark_failed`).

## Public API

### `WebhookEventType` (Enum)
Event types: `CONTENT_ADDED` ("content.added"), `CONTENT_UPDATED`,
`CONTENT_DELETED`, `BOOKMARK_ADDED`, `BOOKMARK_REMOVED`, `TAG_ADDED`,
`TAG_REMOVED`, `CRAWL_STARTED`, `CRAWL_COMPLETED`, `COLLECTION_CHANGED`.

### `WebhookEndpoint` (dataclass)
Fields: `endpoint_id: str`, `url: str`, `secret: str | None = None`,
`events: list[WebhookEventType] = []`, `enabled: bool = True`,
`created_at: datetime | None = None` (auto-set to now-UTC in `__post_init__`),
`last_triggered: datetime | None = None`, `failure_count: int = 0`,
`max_retries: int = 3`, `retry_delay: float = 1.0`.
- `should_retry() -> bool`: `failure_count < max_retries`.

### `WebhookPayload` (dataclass)
Fields: `payload_id: str`, `event_type: WebhookEventType`, `data: dict[str, Any]`,
`endpoint_id: str`, `url: str`, `attempts: int = 0`, `delivered: bool = False`,
`delivered_at: datetime | None = None`, `last_error: str | None = None`,
`signature: str | None = None`, `next_retry_at: datetime | None = None`
(None when delivered or when no retry is scheduled).

### `WebhookManager`
State: `endpoints: dict[str, WebhookEndpoint]`, `pending: list[WebhookPayload]`,
`delivered: list[WebhookPayload]`, private `_id_counter`.
- `register_endpoint(url, events=None, secret=None, **kwargs) -> WebhookEndpoint`:
  assigns `wh-<n>` id; `events=None` subscribes to **ALL** event types;
  extra `**kwargs` are forwarded to the `WebhookEndpoint` constructor.
- `remove_endpoint(endpoint_id) -> bool`: True if present, else False.
- `dispatch_event(event_type, data) -> list[WebhookPayload]`: for each **enabled**
  endpoint whose `events` include `event_type`, creates a payload, appends to
  `pending`, and stamps `last_triggered`. Disabled endpoints and non-subscribed
  endpoints are skipped. Returns the created payloads (empty list if none match).
- `get_pending() -> list[WebhookPayload]` / `get_delivered() -> list[WebhookPayload]`.
- `mark_delivered(payload_id) -> bool`: moves the payload from `pending` to
  `delivered`, sets `delivered`/`delivered_at`, and **resets the endpoint's
  `failure_count` to 0**. False if the id is not pending.
- `mark_failed(payload_id, error) -> bool`: increments `attempts` and the
  endpoint's `failure_count`, sets `last_error`. If `should_retry()` still holds,
  schedules `next_retry_at = now + retry_delay` (payload stays pending);
  otherwise sets `next_retry_at = None` and **drops the payload into `delivered`**
  (i.e. exhausted payloads land in `delivered` with `delivered=False`).
  False if the id is not pending.
- `get_stats() -> dict[str, Any]`: `total_endpoints`, `enabled_endpoints`,
  `pending_payloads`, `delivered_payloads`.
- `get_payload_json(payload) -> str`: JSON body `{"event", "timestamp", "data"}`
  with `sort_keys=True`.

## Contract holes
- **Signature does not verify against the delivered body.** `_create_payload`
  signs a body whose `timestamp` is captured at creation time, but
  `get_payload_json` regenerates a **fresh** `timestamp` on every call. The
  signed body is never stored, so a receiver that recomputes the HMAC over
  `get_payload_json(payload)` will get a different digest than `payload.signature`.
  The signature is therefore non-verifiable as shipped.
- **Exhausted payloads are indistinguishable from delivered ones.** `mark_failed`
  moves a retry-exhausted payload into the `delivered` list with
  `delivered=False`, and `get_stats()["delivered_payloads"]` counts it. There is
  no separate "failed/dropped" bucket, so a caller cannot tell success from
  permanent failure by list membership alone (must inspect `payload.delivered`).
- **No HTTP delivery / no retry loop.** The manager only schedules
  `next_retry_at`; nothing reads it or re-dispatches. Retries are the caller's
  responsibility, and `next_retry_at` is never consulted by any manager method.
- **`register_endpoint` accepts arbitrary `**kwargs`.** Unknown kwargs are passed
  straight to the `WebhookEndpoint` dataclass and raise `TypeError` at runtime
  rather than being validated up front.
