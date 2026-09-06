# TICKET-511: URLVisit.to_dict placeholder docstring (name-echo)

Status: OPEN
File: personal_index/url_history.py
Line: 30
Symptom: `URLVisit.to_dict` docstring is the placeholder `"""To_dict."""`
  (echoes the method name, describes no behavior).
Evidence:
  - personal_index/url_history.py:30  `"""To_dict."""`
  - Live behavior (verified): returns a NEW dict each call (not the same
    object); exactly 8 keys in dataclass declaration order
    (url, timestamp, status_code, content_length, title, user_agent,
    response_time_ms, error); values are the field values; round-trips with
    URLVisit.from_dict (from_dict(to_dict(v)) == v). Pure: does not mutate
    self.
Minimal additive fix:
  - Reword ONLY to_dict's docstring to state the exact contract above.
  - Add pinning tests (TestURLVisitToDict): returns dict type, exact key set
    + order, fresh object per call, values match fields, round-trip with
    from_dict, does not mutate self.
Issue: #878
