# webhook — spec

> **DEAD MODULE — 0 importers.** `personal_index/webhook.py` is never imported
> or registered anywhere in `personal_index/` (witness:
> `grep -rn 'import webhook\|from personal_index.webhook\|from .webhook'
> personal_index/ --include=*.py` returns nothing, rc=1). It is a dead parallel
> implementation. Its only consumer is the test suite
> (`tests/test_webhook.py`).
>
> **NEAR-NAME-COLLISION DISAMBIGUATION.** This page documents
> `personal_index/webhook.py` (the **fire-and-forget sender**: `WebhookSender`
> + `add_endpoint`/`send`, no persistent state). It is a DIFFERENT module from
> `personal_index/content_webhooks.py` (the **record-and-track manager**:
> `WebhookManager` + `register_endpoint`/`dispatch_event`/`get_stats` + HMAC
> `_sign`), which is the live integration and is covered by
> [content-webhooks.md](content-webhooks.md). The two modules share the class
> names `WebhookPayload` (and a near-name `WebhookEvent`/`WebhookEventType`)
> but have **divergent, incompatible contracts** — do not conflate them. The
> live twin is `content_webhooks` (imported by the pipeline); this module is
> dead.

## Purpose

A standalone webhook **fire-and-forget sender**: build a `WebhookPayload`,
attach one or more `WebhookConfig` endpoints via `add_endpoint`, and `send()`
POSTs the payload to every matching endpoint and returns a transient
per-endpoint result list. It keeps **no persistent record** of what was
delivered or failed, and it **never signs** payloads. This is the opposite of
the live twin's record-and-track model (which persists `pending`/`delivered`
payloads, tracks per-endpoint retry state, and HMAC-signs every body).

## Public API

### Enums
- `WebhookEvent` (webhook.py:18) — `str` Enum, 6 members
  (`CRAWL_COMPLETE`, `CRAWL_FAILED`, `INDEX_UPDATE`, `ERROR_OCCURRED`,
  `HEALTH_CHECK`, `BACKUP_COMPLETE`; values are the lower-snake strings).

### `WebhookPayload` (dataclass, webhook.py:29)
Fields: `event: WebhookEvent`, `data: dict[str, Any] = {}`,
`timestamp: float = time.time()`, `source: str = "personal-index"`.
- `to_dict()` (webhook.py:37) — exactly four keys: `event` (the enum's
  `.value` string, not the enum object), `data`, `timestamp` (float),
  `source` (str).
- `to_json()` (webhook.py:51) — `json.dumps(self.to_dict())`.

> **Divergence from the live twin.** The live twin's `WebhookPayload`
> (content_webhooks.py:72) carries **delivery-tracking state** (a payload id
> and a delivered/failed status) so the manager can query history; this
> module's `WebhookPayload` is a **bare value object** with no id and no
> delivery status — it cannot be tracked after `send()` returns.

### `WebhookConfig` (dataclass, webhook.py:57)
Fields: `url: str`, `events: list[WebhookEvent] = []`,
`headers: dict[str, str] = {}`, `timeout: float = 10.0`,
`retry_count: int = 3`, `retry_delay: float = 1.0`, `enabled: bool = True`.
- `should_send(event)` (webhook.py:68) — `False` when `enabled` is `False`
  (checked first); `True` for every event when `events` is empty; otherwise
  `True` only when `event in self.events`.

### `WebhookSender` (webhook.py:83)
- `add_endpoint(config)` (webhook.py:89) — appends `config` to the internal
  `_configs` list in call order; **no URL validation, no de-duplication**;
  returns `None`.
- `remove_endpoint(url) -> bool` (webhook.py:97) — removes the **first**
  config whose `url` equals `url` and returns `True`; returns `False` and
  leaves the list unchanged when no config matches.
- `send(payload) -> list[dict]` (webhook.py:110) — for each config whose
  `should_send(payload.event)` is `True`, calls `_send_to_endpoint` and
  appends the returned dict; returns the **transient** list. **Nothing is
  stored** — there is no `get_delivered`/`get_pending`/`get_stats`.
- `_validate_url_scheme(url) -> str | None` (webhook.py:120) — returns an
  error string when the parsed scheme is not `http`/`https`, else `None`.
- `_build_request(config, payload) -> Request` (webhook.py:128) — a `POST`
  `Request` with `Content-Type: application/json` merged over `config.headers`
  and the JSON body.
- `_send_to_endpoint(config, payload) -> dict` (webhook.py:138) — short-circuits
  to a failure dict (`success: False`, `attempts: 0`) on a bad scheme;
  otherwise loops `range(config.retry_count + 1)` attempts, returning a
  success dict (`status`, `success: True`, `attempts`) on the first
  `urlopen` success, or a failure dict (`success: False`, `error`,
  `attempts: config.retry_count + 1`) after all attempts raise
  `URLError`/`OSError`/`TimeoutError` (sleeping `retry_delay` between attempts).
- `endpoint_count` (property, webhook.py:174) — `len(self._configs)`.

## Invariants

1. `send()` returns a **transient** `list[dict]` of per-endpoint results and
   keeps **no persistent record** — after it returns, the sender cannot answer
   "what was delivered / what failed / how many endpoints" beyond
   `endpoint_count` (which counts configs, not deliveries).
2. `send()` performs a **per-call retry loop** (`retry_count + 1` attempts)
   inside `_send_to_endpoint`, but this is **ephemeral** — it is not the live
   twin's persistent per-endpoint `failure_count`/`should_retry` state.
3. Payloads are **never signed**: `_build_request` (webhook.py:128) sets only
   `Content-Type` + `config.headers`; there is no `_sign`/HMAC, so an endpoint
   that verifies a signature header will reject every payload this module
   sends.
4. `add_endpoint` does not validate the URL scheme; a bad scheme is only
   caught at `send()` time (as a per-endpoint failure dict, not an exception).

## Known contract holes

- **ARCH-107** — the dead module keeps **no persistent delivery/failure
  tracking** and **never signs payloads**, diverging from the live twin's
  record-and-track + HMAC contract: `WebhookSender.send()` (webhook.py:110)
  returns a transient `list[dict]` and offers no `get_delivered`/`get_pending`/
  `get_stats`, while the live twin's `WebhookManager` persists `pending`/
  `delivered` payloads and exposes `get_stats()` (content_webhooks.py:231); and
  this module has no `_sign`/HMAC, while the live twin signs every body with
  `WebhookManager._sign` (content_webhooks.py:270). A consumer mirroring the
  live contract (querying delivery history / retry state, or verifying a
  signature) cannot do so against the dead module. See tickets/ARCH-107.md.
