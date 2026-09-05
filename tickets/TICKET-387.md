# TICKET-387: webhook.py placeholder docstrings (class-(b) doc-drift)

Status: RESOLVED (merged to main 298db36, gh #612 closed)

## File
personal_index/webhook.py

## Symptom
Three methods carry generic `"""Process <name>.` placeholders that do not
describe the exact conditionals the bodies perform:
- `WebhookConfig.should_send` (line 63): returns False when `enabled` is
  False (before any event check); when enabled and `events` is empty, returns
  True for every event; otherwise returns True only when `event in self.events`.
- `WebhookSender.add_endpoint` (line 82): appends the config to the internal
  `_configs` list in call order (no validation / de-duplication); returns None.
- `WebhookSender.remove_endpoint` (line 90): scans in order, removes the FIRST
  config whose `url` matches and returns True; when none matches, leaves the
  list unchanged and returns False.

## Evidence
- L64: `"""Process should_send.` — body: `if not self.enabled: return False`;
  `if not self.events: return True`; `return event in self.events`.
- L83: `"""Process add_endpoint.` — body: `self._configs.append(config)`.
- L91: `"""Process remove_endpoint.` — body: `for i, config in enumerate(...)`:
  `if config.url == url: self._configs.pop(i); return True`; `return False`.

## Minimal additive fix
Reword each placeholder to state the exact conditional the body performs. Add
ONE pinning behavior test: a disabled config whose `events` list DOES contain
the event still returns False (the `enabled` short-circuit fires before the
membership check) — pinning the corrected `should_send` claim and asserting the
sibling condition (event-in-list) is present while the send is absent.

Issue: #612

## Status
RESOLVED
