# TICKET-313: content_backup/backup_store.py import_from_file unguarded datetime.fromisoformat ValueError on corrupt timestamp

- Status: OPEN
- Module: personal_index/content_backup/backup_store.py
- Symptom: `BackupStore.import_from_file` already guards the decode step — it raises a clean
  `ValueError` on non-JSON input and on a non-dict payload, and wraps the `BackupEntry(...)`
  construction in `except KeyError` to raise a clean `ValueError` on a missing required key.
  But the very next step in the same untrusted-input chain — the
  `datetime.fromisoformat(data["timestamp"])` call inside that same `try` block — raises
  `ValueError` on a corrupt timestamp string (e.g. `"not-a-timestamp"`), which is NOT in the
  `except KeyError` clause. A valid-JSON dict whose `timestamp` is a non-ISO string therefore
  escapes `import_from_file` as a raw `ValueError` traceback instead of the method's documented
  clean `ValueError` contract. This is the exact cycle-43 (TICKET-312) pattern applied to a
  sibling import path: the degrade/clean-error invariant must cover EVERY value-construction
  step, not just the decode.
- Evidence: personal_index/content_backup/backup_store.py lines 179-189 — the `try:` block
  builds `BackupEntry(backup_id=data["backup_id"], timestamp=datetime.fromisoformat(
  data["timestamp"]), item_count=data["item_count"], data=data["items"], ...)` and the `except`
  clause is `except KeyError as exc:` only (no `ValueError`).
  `python3 -c "import json,tempfile,os; from personal_index.content_backup.backup_store import BackupStore; p=os.path.join(tempfile.mkdtemp(),'b.json'); json.dump({'backup_id':'x','timestamp':'not-a-timestamp','item_count':0,'items':[]},open(p,'w')); BackupStore().import_from_file(p)"`
  -> `ValueError: Invalid isoformat string: 'not-a-timestamp'` (raw traceback, not the
  documented clean `ValueError`).
- Minimal additive fix: add `ValueError` to the `except` clause (i.e.
  `except (KeyError, ValueError) as exc:`) so a corrupt `timestamp` raises the same clean
  `ValueError` contract as a missing key. No change to the happy path.
- Issue: #461
