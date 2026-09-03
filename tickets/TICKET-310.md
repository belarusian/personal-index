# TICKET-310: session.py load_session unguarded SessionStatus() on invalid status string

- Status: RESOLVED
- Module: personal_index/session.py
- Symptom: `SessionManager.load_session` guards `json.JSONDecodeError` (TICKET-298) and a
  non-dict payload, but then constructs `SessionStatus(data.get("status", "active"))` from
  untrusted disk input with no guard. A valid-JSON file whose `status` field is not one of the
  five enum values (e.g. `"status": "bogus"`) makes `SessionStatus(...)` raise
  `ValueError: 'bogus' is not a valid SessionStatus`, escaping `load_session` as a traceback.
- Evidence: personal_index/session.py line 302 (`status=SessionStatus(data.get("status", "active"))`);
  `python3 -c "from personal_index.session import SessionStatus; SessionStatus('bogus')"` ->
  `ValueError: 'bogus' is not a valid SessionStatus`. The existing guard (lines 295-298) only
  catches `json.JSONDecodeError`, not the downstream enum construction.
- Minimal additive fix: wrap the `SessionStatus(...)` construction in `try/except ValueError`
  and degrade to `return None`, matching the established corrupt-input contract of this method
  (corrupt/truncated JSON -> None, non-dict -> None). No change to the happy path.
- Issue: #455
