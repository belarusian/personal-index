# ARCH-107 — webhook.py `WebhookSender` keeps no persistent delivery/failure tracking and never signs payloads, diverging from the live twin's record-and-track + HMAC contract

- **Status:** CLOSED (architect close, cycle 319; was VERIFIED (validator cycle 271 @ main 76e12b6; _sign HMAC-SHA256 at webhook.py:169-178, get_pending/get_delivered at :221-225; pinning tests tests/test_webhook.py 26 passed; adversarial: _sign('hello','secret') == hmac.new(b'secret',b'hello',sha256).hexdigest(); [was IMPLEMENTED #1584@6e3d6112]))
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/webhook.py (DEAD module — 0 importers; see docs/webhook.md) + personal_index/content_webhooks.py (the live record-and-track + HMAC twin it was meant to mirror)
- **Issue:** #1522

## Symptom

`webhook.py` is a dead parallel implementation of the webhook system: it is
never imported anywhere in `personal_index/` (witness below), and it is a
**fire-and-forget sender** (`WebhookSender` + `add_endpoint`/`send`) where the
live twin `content_webhooks.py` is a **record-and-track manager**
(`WebhookManager` + `register_endpoint`/`dispatch_event`/`get_stats` + HMAC
`_sign`). The two modules share the class name `WebhookPayload` (and a
near-name `WebhookEvent`/`WebhookEventType`) but their contracts have silently
diverged.

The concrete, verifiable holes are two:

1. **No persistent delivery/failure tracking.** The dead module's
   `WebhookSender.send()` (webhook.py:110) returns a **transient**
   `list[dict]` of per-endpoint results and keeps **no record** of what was
   delivered or failed — there is no `get_delivered`/`get_pending`/`get_stats`
   and no `pending`/`delivered` store. The live twin's `WebhookManager`
   persists `pending`/`delivered` payloads and exposes
   `get_pending()` (content_webhooks.py:186), `get_delivered()`
   (content_webhooks.py:190), `mark_delivered()` (content_webhooks.py:194),
   `mark_failed()` (content_webhooks.py:209), and `get_stats()`
   (content_webhooks.py:231). A consumer mirroring the live contract (querying
   delivery history / retry state) cannot do so against the dead module.

2. **No HMAC signing.** The dead module never signs payloads:
   `_build_request` (webhook.py:128) sets only `Content-Type` +
   `config.headers`, and there is no `_sign`/HMAC anywhere in the module. The
   live twin signs every body with `WebhookManager._sign`
   (content_webhooks.py:270, `hmac.new(secret, body, sha256).hexdigest()`). An
   endpoint that verifies a signature header will reject every payload the
   dead module sends.

Note (correction to the cycle-277 briefing): the dead module DOES perform a
**per-call retry loop** in `_send_to_endpoint` (webhook.py:138-172,
`for attempt in range(config.retry_count + 1)` with `time.sleep(retry_delay)`
between attempts). That retry is **ephemeral** — it is not the live twin's
persistent per-endpoint `failure_count`/`should_retry` state
(content_webhooks.py:66). The genuine divergences are the two holes above, not
"no retry".

This is the dead-module + divergent-contract class (ARCH-100/102/105/106
pattern): the module ships a public `send` API whose contract (queryable
delivery history + signed bodies) it does not fulfill, and which is
incompatible with the live twin it was meant to mirror.

## Evidence (file:line)

DEAD-MODULE witness:
- `grep -rn 'import webhook\|from personal_index.webhook\|from .webhook'
  personal_index/ --include=*.py` returns **nothing** (rc=1) — webhook.py is
  never wired.
- Its only consumer is the test suite: `tests/test_webhook.py`
  (`from personal_index.webhook import ...`).

Dead-module delivery-tracking (transient, no store):
- personal_index/webhook.py:110 — `def send(self, payload) -> list[dict]:`.
- personal_index/webhook.py:111-117 — body builds a local `results` list,
  appends each `_send_to_endpoint` dict, and `return results`; **nothing is
  stored on `self`** (only `_configs` is kept).
- personal_index/webhook.py:83-87 — `WebhookSender.__init__` sets only
  `self._configs: list[WebhookConfig] = []`; there is no `pending`/`delivered`
  attribute.
- personal_index/webhook.py:174-176 — `endpoint_count` returns
  `len(self._configs)` (counts configs, not deliveries).
- No `get_delivered`/`get_pending`/`get_stats`/`mark_delivered`/`mark_failed`
  method exists anywhere in the module.

Dead-module signing (absent):
- personal_index/webhook.py:128-136 — `_build_request` sets headers
  `{"Content-Type": "application/json", **config.headers}`; **no signature
  header is added**.
- No `_sign` method and no `import hmac`/`hashlib` in the module (imports are
  `json`, `logging`, `time`, `urllib.request`, `dataclasses`, `enum`,
  `typing`, `urllib.error`).

Live-twin delivery-tracking + signing — the contract the dead module diverges
from:
- personal_index/content_webhooks.py:186 — `def get_pending(self)`.
- personal_index/content_webhooks.py:190 — `def get_delivered(self)`.
- personal_index/content_webhooks.py:194 — `def mark_delivered(self, payload_id)`.
- personal_index/content_webhooks.py:209 — `def mark_failed(self, payload_id, error)`.
- personal_index/content_webhooks.py:231 — `def get_stats(self) -> dict[str, Any]:`
  (returns `total_endpoints`/`enabled_endpoints`/`pending_payloads`/
  `delivered_payloads`).
- personal_index/content_webhooks.py:270 — `def _sign(self, body, secret) -> str:`
  (`hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()`).
- personal_index/content_webhooks.py:66 — `def should_retry(self) -> bool:`
  (persistent per-endpoint retry state, unlike the dead module's ephemeral
  per-call loop).

## Proposed fix (implementer)

Two acceptable resolutions; pick one and record it in the ticket:

(a) **Align the dead module to the live twin's contract** (preferred if the
    module is ever revived): add persistent `pending`/`delivered` stores to
    `WebhookSender` (webhook.py:83) plus `get_pending()`/`get_delivered()`/
    `get_stats()` accessors mirroring the live twin, and add a `_sign`/HMAC
    path so `WebhookConfig` can carry a `secret` and `_build_request`
    (webhook.py:128) attaches a signature header — so delivery history is
    queryable and bodies are signed, matching the live twin.

(b) **Explicitly defer / document the divergence** (if the module stays dead):
    keep `send()` transient and unsigned, but state in the `WebhookSender`
    docstring and in docs/webhook.md that `send()` returns a **transient**
    result list with **no persistent delivery/failure tracking** and that
    payloads are **never signed** — and that this is intentionally NOT the
    live twin's `get_stats`/`_sign` contract — so a future reader does not
    assume the two are interchangeable.

Either way, the docs/webhook.md "Known contract holes" entry must reflect the
chosen resolution.

## Resolution (implementer, cycle 335)

Chose **(a) — align the dead module to the live twin's contract** (the
ARCH-106 pattern). `WebhookSender` now keeps persistent `pending`/`delivered`
stores, exposes `get_pending()`/`get_delivered()`/`get_stats()` mirroring
`content_webhooks.WebhookManager`, and `WebhookConfig` carries an optional
`secret`; `_build_request` attaches an `X-Signature` HMAC-SHA256 header via a
new `_sign()` when a secret is set. `send()` records each matching payload in
`pending` before dispatch and moves it to `delivered` on success. The
docs/webhook.md update (dead-module status, near-name distinction, resolution
(a) reflection) is DEFERRED to the architect (docs/** is architect-owned).

## Acceptance criteria

- [ ] The dead-module status (0 importers) is stated in docs/webhook.md header
      (done in this PR) and in this ticket.
- [ ] The near-name distinction from `content_webhooks.py` is stated in the
      page header (done in this PR).
- [ ] The transient-`send`/no-store + no-HMAC divergences are pinned with
      file:line evidence (above).
- [ ] A resolution (a) or (b) is chosen and the docs page updated to match.
- [ ] Pinning test (implementer, tests/** — NOT the architect's path): one
      behavior test that constructs a `WebhookSender`, adds an endpoint, calls
      `send()`, and asserts the delivery-tracking contract the chosen
      resolution states — for (a) assert `get_stats()`/`get_delivered()`
      reflect the send (guard path: a fresh sender has empty
      `get_pending()`/`get_delivered()`); for (b) assert `send()` returns a
      `list[dict]` and that no `get_delivered`/`get_stats`/`_sign` attribute
      exists on the sender, pinning the documented divergence.

## Self-review checklist (architect)

- [x] Component + public contract (signature, behavior, error paths, guard
      inputs) stated.
- [x] Acceptance criteria present.
- [x] Pinning test specified (implementer's to write; architect never writes
      tests/**).
- [x] Matching docs/webhook.md update shipped in the SAME PR.
- [x] DEAD-MODULE witness (0 importers) recorded.
- [x] Near-name-collision disambiguation (webhook vs content_webhooks)
      recorded.
- [x] No personal_index/** or tests/** written by the architect.

## Docs reconciled (architect, cycle 301)
The deferred docs cleanup is closed: docs/webhook.md header blockquote,
Purpose section, public-surface table (WebhookConfig.secret, send()
pending/delivered recording, _build_request X-Signature, new
get_pending/get_delivered/get_stats/_sign rows), Invariants 1 & 3, and the
Known-contract-holes ARCH-107 bullet are all restated to the confirmed
resolution (a) outcome. No status change.
## Index line reconciled (architect, cycle 304)
The docs/README.md index line for webhook.md still carried the open-hole
framing ("transient-send-no-store + no-HMAC-signing contract holes") after
the module page was reconciled in cycle 301; it is now restated to the
confirmed resolution (a) contract (persistent pending/delivered stores +
X-Signature HMAC-SHA256 via _sign when a secret is set). No status change.
