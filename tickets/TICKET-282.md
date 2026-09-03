# TICKET-282: content_timeline/timeline_event.py from_dict unguarded fromisoformat + keyed access

- Status: OPEN
- Issue: #398
- Module: personal_index/content_timeline/timeline_event.py
- Class: unguarded type-assumption (datetime.fromisoformat on unvalidated external string -> ValueError; data[key] on unvalidated external dict -> KeyError)

## Symptom
`TimelineEvent.from_dict(data)` (line 56) is a deserialization boundary. Two unguarded
sites raise on malformed external input:
1. `ts = data.get("timestamp", <default iso>)` (line 62) then
   `ts = datetime.fromisoformat(ts)` (line 64) — if the timestamp is present but not a
   valid ISO string (e.g. "not-a-date"), `fromisoformat` raises `ValueError`.
2. `event_id=data["event_id"]` (line 67) and `content_id=data["content_id"]` (line 70)
   — unguarded keyed access; a record missing either key raises `KeyError`.

Both crash the caller (`Timeline.from_dict`, timeline.py:132) instead of degrading.

## Evidence
- personal_index/content_timeline/timeline_event.py:62  `ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())`
- personal_index/content_timeline/timeline_event.py:64  `ts = datetime.fromisoformat(ts)`   <- unguarded, ValueError on bad string
- personal_index/content_timeline/timeline_event.py:67  `event_id=data["event_id"]`          <- unguarded keyed access, KeyError
- personal_index/content_timeline/timeline_event.py:70  `content_id=data["content_id"]`      <- unguarded keyed access, KeyError
- Runtime: from_dict({'event_id':'e1','content_id':'c1','timestamp':'not-a-date'}) -> ValueError
           from_dict({'content_id':'c1'}) -> KeyError 'event_id'
           from_dict({'event_id':'e1'})   -> KeyError 'content_id'

## Writer type (verified)
`to_dict()` (line 37) always emits `timestamp` as `self.timestamp.isoformat()` (a valid
ISO string) and always includes `event_id`/`content_id`. So the writer is well-formed;
the guard protects the *reader* against externally-produced / hand-edited / corrupted
records (the deserialization boundary), matching the module's lenient `.get()`-with-default
degrade contract used for every other field.

## Degrade contract (verified)
Every other field in `from_dict` uses `data.get(key, default)`. The timestamp already has a
default (now) for the *missing* case; the gap is the *present-but-invalid* case. The guard
degrades a bad timestamp to the same default (now) the missing case uses, and degrades
missing `event_id`/`content_id` to `""` like the other string fields.

## Minimal additive fix
- Wrap `datetime.fromisoformat(ts)` in `try/except ValueError` -> `ts = datetime.now(timezone.utc)`.
- `event_id=data.get("event_id", "")` and `content_id=data.get("content_id", "")`.

## Regression tests (tests/test_content_timeline.py)
- bad-timestamp -> degrades to a datetime (no ValueError), other fields preserved
- missing event_id -> "" (no KeyError)
- missing content_id -> "" (no KeyError)
- valid record still round-trips (regression guard)
