# TICKET-225: Duplicate webhook functionality

## Evidence
- `personal_index/webhook.py`: WebhookEvent enum, WebhookPayload, HTTP delivery via urllib
- `personal_index/content_webhooks.py`: WebhookEventType enum, webhook delivery with HMAC signing and retry logic
- Both handle event notification to external endpoints

## Impact
- Two webhook systems with different event taxonomies
- Risk of missed notifications if only one is wired up

## Suggestion
Consolidate into a single webhook module with unified event types and delivery logic.
