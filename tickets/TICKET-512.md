# TICKET-512: ContentVersion.to_dict placeholder docstring (name-echo)

Status: RESOLVED (merged via PR #883, issue #882 closed)
File: personal_index/versioning.py
Line: 26
Symptom: `ContentVersion.to_dict` docstring is the placeholder `"""To_dict."""`
  (echoes the method name, describes no behavior).
Evidence:
  - personal_index/versioning.py:26  `"""To_dict."""`
  - Live behavior (verified): returns a NEW dict each call (fresh object);
    exactly 7 keys in dataclass declaration order (url, version_id,
    content_hash, title, content_length, captured_at, metadata); captured_at
    is serialized to an ISO-8601 string via .isoformat(); metadata is the
    SAME dict reference (not copied); pure (does not mutate self).
Minimal additive fix:
  - Reword ONLY to_dict's docstring to state the exact contract above.
  - Add pinning tests (TestContentVersionToDict): returns dict type, exact
    key set + order, captured_at is ISO string, metadata same reference,
    fresh object per call, does not mutate self.
Note: renumbered from 511 to 512 — in-flight competitor PR #881 (build146)
  holds TICKET-511 for url_history.py URLVisit.to_dict (same sweep, different
  file); 511 would collide when #881 merges.
Issue: #882
