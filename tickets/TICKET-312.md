# TICKET-312: scheduler.py ScheduleStore._load unguarded datetime.fromisoformat ValueError on corrupt timestamp

- Status: OPEN
- Module: personal_index/scheduler.py
- Symptom: `ScheduleStore._load` already degrades to an empty store on corrupt JSON, a
  non-dict payload, and a missing `config`/key (TICKET-265) via
  `except (json.JSONDecodeError, KeyError, TypeError)`. But the very next step in the same
  untrusted-input chain — the `datetime.fromisoformat(entry_data["last_run"])` /
  `datetime.fromisoformat(entry_data["next_run"])` calls — raises `ValueError` on a corrupt
  timestamp string (e.g. `"not-a-timestamp"`), which is NOT in the except clause. A valid-JSON
  dict whose `last_run`/`next_run` is a non-ISO string therefore escapes `_load` (and thus the
  `ScheduleStore.__post_init__` constructor) as a raw `ValueError` traceback instead of
  degrading to an empty store. This violates the method's own corrupt-input contract established
  by the TICKET-265 guard and the degrade-to-None invariant.
- Evidence: personal_index/scheduler.py lines 67-73 (`datetime.fromisoformat(entry_data["last_run"])`
  / `fromisoformat(entry_data["next_run"])`) vs. line 86 (`except (json.JSONDecodeError,
  KeyError, TypeError)` — no `ValueError`).
  `python3 -c "import json,tempfile,os; from personal_index.scheduler import ScheduleStore;
  p=os.path.join(tempfile.mkdtemp(),'s.json'); json.dump({'j':{'config':{'interval_hours':24,'enabled':True,'seed_urls':[],'max_pages_per_run':50,'crawl_depth':2,'delay':1.0},'last_run':'not-a-timestamp','next_run':None,'run_count':0,'total_pages_indexed':0}},open(p,'w')); ScheduleStore(path=p)"`
  -> `ValueError: Invalid isoformat string: 'not-a-timestamp'`. The TICKET-265 guard (line 86)
  does not cover the downstream `fromisoformat` calls.
- Minimal additive fix: add `ValueError` to the `_load` except clause (i.e.
  `except (json.JSONDecodeError, KeyError, TypeError, ValueError)`) so a corrupt timestamp
  degrades to an empty store, matching the established corrupt-input contract. No change to the
  happy path.
- Issue: #459
