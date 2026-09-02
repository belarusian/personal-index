# TICKET-268: bookmarks.py BookmarkManager.load non-list JSON guard

## File
personal_index/bookmarks.py

## Symptom
`BookmarkManager.load()` crashes when the JSON file contains a non-list value
(null, dict, number). The `save()` method writes a JSON list, so `load()`
expects a list. If the file is corrupted or hand-edited to contain `null`,
`{"key": "val"}`, or `42`, the `for item in data:` loop raises
`TypeError` (NoneType/int not iterable) or `AttributeError` (dict iteration
yields keys, `Bookmark.from_dict(str)` fails).

## Evidence
- Line 157: `data = json.load(f)` — no isinstance guard
- Line 159: `for item in data:` — assumes list
- No try/except wrapping the json.load call
- Same class as TICKET-265 (scheduler.py), TICKET-266 (content_pin.py), TICKET-267 (tags.py)

## Minimal Additive Fix
After `data = json.load(f)` (line 157), add: