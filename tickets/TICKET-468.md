# TICKET-468: BookmarkManager.load docstring omits guard predicates

- File: personal_index/bookmarks.py
- Method: BookmarkManager.load
- Symptom (class-b doc drift): docstring is the blanket claim
  "Load bookmarks from JSON file. Returns count loaded." while the body
  applies NAMED guards:
    * raises ValueError when neither `path` nor the configured storage
      path is set;
    * returns 0 WITHOUT touching the current set when the file is missing,
      the JSON is malformed (JSONDecodeError), or the top-level JSON value
      is not a list (self._bookmarks.clear() runs only after the
      isinstance(data, list) check);
    * otherwise replaces the current set with the loaded bookmarks and
      returns the number loaded.
- Evidence line: `def load` docstring (line ~150) vs body guards
  (path_obj.exists() / except JSONDecodeError / isinstance(data, list)).
- Minimal additive fix: reword the docstring to state the exact guards and
  the replace-vs-preserve semantics; add ONE behavior test pinning the
  corrected claim (normal: valid list replaces set + returns count; guard:
  non-list top-level returns 0 and leaves the existing set untouched).
- Status: OPEN
- Issue: #779
