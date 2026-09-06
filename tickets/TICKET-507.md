# TICKET-507: webhook.py placeholder docstrings under-describe behavior

- **File:** personal_index/webhook.py
- **Methods:** `WebhookPayload.to_dict` (line 38), `WebhookPayload.to_json` (line 47), `WebhookSender.endpoint_count` (line 170)
- **Defect class:** (b) docstring drift (under-specification)
- **Symptom:** Three docstrings are bare name-echo placeholders ("To_dict.", "To_json.", "Endpoint_count.") that state no behavior the body performs.
- **Evidence:**
  - L38 `to_dict`: body returns `{"event": self.event.value, "data": self.data, "timestamp": self.timestamp, "source": self.source}` — i.e. a dict with exactly the four keys event (the enum's `.value` string, not the enum), data (the payload dict), timestamp (float), source (str).
  - L47 `to_json`: body returns `json.dumps(self.to_dict())` — i.e. the JSON string of the to_dict() mapping.
  - L170 `endpoint_count`: body is a `@property` returning `len(self._configs)` — i.e. the number of configured endpoints.
- **Minimal additive fix:** Reword each placeholder to state the exact behavior the body performs (enumerate the four to_dict keys and that event is the `.value` string; to_json is json.dumps of to_dict; endpoint_count is len of the config list). Add ONE pinning behavior test that asserts the to_dict() returned object has exactly the four documented keys (event as the `.value` string, data, timestamp, source) and asserts the ABSENCE of any sibling key (e.g. the enum object itself is not a key), so the doc-only fix is witnessed.
- **Issue:** #868
- **Status:** OPEN
