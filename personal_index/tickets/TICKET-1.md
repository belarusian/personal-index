# TICKET-1: Webhook URL open without scheme validation (S310)

## Evidence
- `personal_index/webhook.py`, lines 117-123
- `urllib.request.urlopen()` is called with `config.url` directly, without validating the URL scheme
- Ruff rule S310: "Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected."
