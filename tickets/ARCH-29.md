# ARCH-29: Webhook signature must be verifiable against the delivered body

Status: CLAIMED 2026-09-10
Component: `personal_index.content_webhooks`
Issue: #1081
Carry-forward: ARCH-2 (#983)

## Symptom
`WebhookManager._create_payload` computes the HMAC signature over a JSON body
whose `timestamp` is captured at creation time. `get_payload_json(payload)`
regenerates a **fresh** `timestamp` on every call. The signed body is never
stored on the payload, so a receiver that recomputes the HMAC over
`get_payload_json(payload)` gets a different digest than `payload.signature`.
The signature is non-verifiable as shipped.

## Public contract (target)
`WebhookPayload` gains a field `body: str` (the exact JSON string that was
signed). `get_payload_json(payload) -> str` returns `payload.body` unchanged
when `payload.body` is set (i.e. the same bytes that were signed), preserving
back-compat for callers that construct a `WebhookPayload` manually without a
`body` (falls back to the current fresh-timestamp serialization).

`_create_payload` stores the signed body on the payload: