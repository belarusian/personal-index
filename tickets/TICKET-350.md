# TICKET-350: content_feed.FeedGenerator.add_item docstring omits sort + max_items cap

- File: personal_index/content_feed.py
- Function: FeedGenerator.add_item (line 103)
- Symptom: docstring says only "Add an item to the feed." but the body also
  (a) sorts self.items by published date, newest first, and (b) truncates
  self.items to self.max_items (default 100) when the cap is exceeded.
- Evidence: lines 104-109 — append, then
  `self.items.sort(key=lambda i: i.published or datetime.min..., reverse=True)`
  and `if len(self.items) > self.max_items: self.items = self.items[: self.max_items]`.
- Fix: reword docstring to state the exact two behaviors (sort by published
  date newest-first; cap at max_items). Add ONE behavior test pinning the
  sort order (newest published first) against the returned items list.
- Class: (b) doc-drift.
- Status: RESOLVED (merged to main, gh #538 closed)
- Issue: #538
