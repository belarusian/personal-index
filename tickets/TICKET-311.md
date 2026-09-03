# TICKET-311: session.py load_session unguarded data["session_id"] KeyError on missing key

- Status: OPEN
- Module: personal_index/session.py
- Symptom: `SessionManager.load_session` already degrades to `None` on corrupt JSON
  (TICKET-298), a non-dict payload, and an invalid `status` string (TICKET-310). But the very
  next step in the same untrusted-input chain — the `CrawlSession(...)` construction — reads
  `session_id=data["session_id"]` with a bare dict subscript. A valid-JSON dict that is missing
  the `session_id` key (e.g. `{"status": "active"}`) makes `data["session_id"]` raise
  `KeyError: 'session_id'`, escaping `load_session` as a raw traceback instead of degrading to
  `None`. This violates the method's own documented contract ("or None if not found") and the
  degrade-to-None invariant established by the two prior guards on this same method.
- Evidence: personal_index/session.py line 306 (`session_id=data["session_id"]`);
  `python3 -c "import json,tempfile,os; from personal_index.session import SessionManager;
  p=tempfile.NamedTemporaryFile('w',suffix='.json',delete=False); json.dump({'status':'active'},p);
  p.close(); SessionManager().load_session(p.name); os.unlink(p.name)"` ->
  `KeyError: 'session_id'`. The existing guards (lines 295-298 JSON, 301-303 status) do not cover
  the downstream `CrawlSession(...)` field access.
- Minimal additive fix: read the required field with a guard that degrades to `None` on a
  missing/empty `session_id` (e.g. `session_id = data.get("session_id")` then `if not
  session_id: return None`), matching the established corrupt-input contract of this method. No
  change to the happy path.
- Issue: #457
