# webhook — spec

> **DEAD MODULE — 0 importers.** `personal_index/webhook.py` is never imported
> or registered anywhere in `personal_index/` (witness:
> `grep -rn 'import webhook\|from personal_index.webhook\|from .webhook'
> personal_index/ --include=*.py` returns nothing, rc=1). It is a dead parallel
> implementation. Its only consumer is the test suite
> (`tests/test_webhook.py`).
>
> **NEAR-NAME-COLLISION DISAMBIGUATION.** This page documents
> `personal_index/webhook.py` (the **record-and-track sender**, resolution (a)
> of ARCH-107: `WebhookSender` + `add_endpoint`/`send` + persistent
> `pending`/`delivered` stores + HMAC `_sign`). It is a DIFFERENT module from
> `personal_index/content_webhooks.py` (the **record-and-track manager**:
> `WebhookManager` + `register_endpoint`/`dispatch_event`/`get_stats` + HMAC
> `_sign`), which is the live integration and is covered by
> [content-webhooks.md](content-webhooks.md). The two modules share the class
> names `WebhookPayload` (and a near-name `WebhookEvent`/`WebhookEventType`)
> and now share the same record-and-track + HMAC contract (resolution (a)
> aligned this module to the live twin). The live twin is `content_webhooks`
> (imported by the pipeline); this module is still dead (0 importers).

## Purpose

A standalone webhook **record-and-track sender** (resolution (a),
ARCH-107, implementer cycle 335 / PR #1584 @ 6e3d6112): build a
`WebhookPayload`, attach one or more `WebhookConfig` endpoints via
`add_endpoint`, and `send()` POSTs the payload to every matching endpoint,
recording each in a persistent `pending` store before dispatch and moving it
to a persistent `delivered` store on success. It exposes `get_pending()`,
`get_delivered()`, and `get_stats()`, and it **signs the body** with the
endpoint's `secret` (HMAC-SHA256, `X-Signature` header) when a secret is set —
mirroring the live twin `content_webhooks.WebhookManager`.

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
`retry_count: int = 3`, `retry_delay: float = 1.0`, `enabled: bool = True`,
`secret: str | None = None` (webhook.py:69).
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
- `send(payload) -> list[dict]` (webhook.py:123) — for each config whose
  `should_send(payload.event)` is `True`, records the payload in the persistent
  `pending` store (webhook.py:135-139), calls `_send_to_endpoint`, and on
  success moves the payload from `pending` to `delivered`; returns the
  per-endpoint result list. No longer purely transient.
- `_validate_url_scheme(url) -> str | None` (webhook.py:120) — returns an
  error string when the parsed scheme is not `http`/`https`, else `None`.
- `_build_request(config, payload) -> Request` (webhook.py:151) — a `POST`
  `Request` with `Content-Type: application/json` merged over `config.headers`
  and the JSON body; when `config.secret` is set it attaches an `X-Signature`
  header via `_sign` (webhook.py:160-161). Unsigned only when no secret is
  configured.
- `_send_to_endpoint(config, payload) -> dict` (webhook.py:138) — short-circuits
  to a failure dict (`success: False`, `attempts: 0`) on a bad scheme;
  otherwise loops `range(config.retry_count + 1)` attempts, returning a
  success dict (`status`, `success: True`, `attempts`) on the first
  `urlopen` success, or a failure dict (`success: False`, `error`,
  `attempts: config.retry_count + 1`) after all attempts raise
  `URLError`/`OSError`/`TimeoutError` (sleeping `retry_delay` between attempts).
- `get_pending() -> list[WebhookPayload]` (webhook.py:221) — returns the
  persistent pending payload store.
- `get_delivered() -> list[WebhookPayload]` (webhook.py:225) — returns the
  persistent delivered payload store.
- `get_stats() -> dict[str, Any]` (webhook.py:229) — returns
  `total_endpoints` / `enabled_endpoints` / `pending_payloads` /
  `delivered_payloads`, mirroring the live twin.
- `_sign(body: str, secret: str) -> str` (webhook.py:169) — HMAC-SHA256 hex
  digest of `body` keyed by `secret`, same construction as the live twin.
- `endpoint_count` (property, webhook.py:174) — `len(self._configs)`.

## Invariants

1. `send()` records each matching payload in the persistent `pending` store
   before dispatch and moves it to `delivered` on success — after it returns,
   the sender CAN answer "what was delivered / what is still pending / how many
   endpoints" via `get_delivered()`/`get_pending()`/`get_stats()`.
2. `send()` performs a **per-call retry loop** (`retry_count + 1` attempts)
   inside `_send_to_endpoint`, but this is **ephemeral** — it is not the live
   twin's persistent per-endpoint `failure_count`/`should_retry` state.
3. Payloads are **signed when a secret is configured**: `_build_request`
   (webhook.py:151) attaches an `X-Signature` header (HMAC-SHA256 hex digest
   via `_sign`) when `config.secret` is set; when no secret is configured the
   body is sent unsigned (no signature header).
4. `add_endpoint` does not validate the URL scheme; a bad scheme is only
   caught at `send()` time (as a per-endpoint failure dict, not an exception).

## Known contract holes

- **ARCH-107 (RESOLVED)** — resolution (a) chosen (implementer, cycle 335 /
  PR #1584 @ 6e3d6112): `send()` now records payloads in persistent
  `pending`/`delivered` stores, `get_pending()`/`get_delivered()`/
  `get_stats()` are exposed, and `_build_request` signs the body with the
  endpoint `secret` (HMAC-SHA256, `X-Signature`) when set — matching the live
  twin's record-and-track + HMAC contract. Pinning witness: implementer's
  `tests/test_webhook.py` (test_fresh_sender_has_empty_stores,
  test_send_tracks_delivered, test_send_failure_keeps_payload_pending,
  test_sign_attaches_signature_header). See tickets/ARCH-107.md.
