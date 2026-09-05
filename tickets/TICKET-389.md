# TICKET-389: url_history.py URLVisit.from_dict placeholder docstring (class-(b) doc-drift)

Status: OPEN

## File
personal_index/url_history.py

## Symptom
`URLVisit.from_dict` (line 43) carries a generic `"""Process from_dict.`
placeholder (with a bare `Args: data.` stub) that does not describe the exact
behavior the body performs.

## Evidence
- L44-47: `"""Process from_dict.\n\nArgs:\ndata.\n"""`
- Body (L48): `return cls(**data)` — unpacks `data` as keyword arguments into
  the `URLVisit` constructor, so each key in `data` must correspond to a
  `URLVisit` field (url, timestamp, status_code, content_length, title,
  user_agent, response_time_ms, error); returns a new `URLVisit` instance.
  Keys absent from `data` fall back to the dataclass defaults.

## Minimal additive fix
Reword the placeholder to state the exact behavior: `from_dict` unpacks
`data` as keyword arguments into the `URLVisit` constructor (`cls(**data)`),
so each key maps to a `URLVisit` field and absent keys take their dataclass
defaults; returns a new `URLVisit`. Add ONE pinning behavior test that passes
a PARTIAL dict (url, status_code, response_time_ms), asserts those exact field
values on the returned object, and asserts the ABSENCE of the sibling keys
(title/content_length/error fall back to their defaults) so the doc-only fix
is witnessed against the returned object.

Issue: #616

## Status
OPEN
