# TICKET-508: WebhookPayload.to_dict placeholder docstring under-describes behavior

Status: OPEN

## File
`personal_index/webhook.py` — `WebhookPayload.to_dict` (line ~38)

## Symptom
The docstring is the placeholder `"""To_dict."""`, which omits the actual contract:
the method returns a NEW `dict` with exactly the keys `event`, `data`, `timestamp`,
`source`; `event` is the enum's `.value` string (not the enum member); `data`,
`timestamp`, and `source` are copied by reference; the payload object is NOT mutated.

## Evidence
Live read of `personal_index/webhook.py` lines 38-46:
    def to_dict(self) -> dict[str, Any]:
        """To_dict."""
        return {
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }
`self.event.value` confirms `event` is the string value, not the enum member.
`self.data` / `self.timestamp` / `self.source` are returned by reference.
No mutation of `self` occurs.

## Minimal additive fix
Reword ONLY `to_dict`'s docstring to state the exact contract above. Do not touch
any other function in webhook.py. Append pinning tests to `tests/test_webhook.py`:
pin return type `dict`, exact key set, `event == enum .value`, and that the payload
is not mutated.

## Issue
Issue: #870 (renumbered from #868; parallel PR #869 claimed TICKET-507 for the same webhook.py finding)
