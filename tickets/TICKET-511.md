# TICKET-511: url_history.py URLVisit.to_dict placeholder docstring under-describes behavior

Status: OPEN

Issue: #878

## File
personal_index/url_history.py

## Symptom
`URLVisit.to_dict` (line 30) carries the bare name-echo placeholder docstring
`"""To_dict."""`. It does not state the actual contract: it returns a dict with
EXACTLY 8 keys — url, timestamp, status_code, content_length, title,
user_agent, response_time_ms, error — each mapped to the corresponding
dataclass field; the method does not mutate state.

## Evidence
- L30: `"""To_dict."""` (name echo, no behavior).
- Body returns a literal dict with the 8 keys above, one per dataclass field.

## Minimal additive fix
Reword the docstring to enumerate the exact 8-key contract and the no-mutation
guarantee. Add ONE pinning behavior test that asserts a field the corrected
docstring newly claims (e.g. response_time_ms) AND the ABSENCE of a sibling key
not in the contract, so the doc-only fix is witnessed against the returned
object.
