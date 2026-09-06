# TICKET-502: ResultsFormatter.max_snippet_length is dead config - create_snippet ignores it

Status: RESOLVED
Issue: #860
Module: personal_index/results.py

## Symptom
`ResultsFormatter.__init__` accepts and stores `max_snippet_length` (line 29-30),
but `create_snippet` (line 58-76) uses its own `max_length` parameter (default 200)
and never reads `self.max_snippet_length`. The constructor config is dead: setting
`max_snippet_length=50` has no effect on snippet length.

## Evidence
Probe: `ResultsFormatter(max_snippet_length=50).create_snippet('x'*500, 'zzz')`
(no-match path) returns 250 chars (200+50), not ~100. Match path
`create_snippet('python '+'y'*500, 'python')` returns 209 chars, not ~100.
The stored `self.max_snippet_length` is never referenced anywhere in the module
(grep: only the __init__ assignment, no read).

## Minimal additive fix
Make `create_snippet`'s `max_length` default to `self.max_snippet_length` when not
explicitly passed (default `max_length: int | None = None`, resolve to
`self.max_snippet_length` when None). This makes the constructor config take effect
while preserving explicit-override behavior. Add a behavior test that pins the
corrected claim against the returned snippet (guard path: no-match truncation uses
the configured length; normal path: match window uses the configured length).
