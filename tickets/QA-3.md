Status: OPEN
Kind: QA
Issue: #1040
Deep test: tests/deep/test_rss_adversarial.py::test_get_recent_entries_negative_count_returns_empty (xfail-strict)

# QA-3: Feed.get_recent_entries leaks Python negative-slice semantics for out-of-range count

## Symptom
`personal_index/rss.py` `Feed.get_recent_entries(count)` is documented as
"Get the most recent entries." and returns `self.entries[:count]`. For an
out-of-range negative `count` (e.g. `count=-1`) it returns `entries[:-1]` -
i.e. ALL entries except the last one - instead of an empty list. `count=0`
correctly returns `[]`, so the guard is missing only for negative values.
Out-of-range (negative) count must yield an empty list, matching the zero
guard.

This is the same defect class as QA-1 (`extract_top_n`) and QA-2
(`rank_documents` / `get_top_terms` / `SearchIndex.search`), but a NEW site:
`Feed.get_recent_entries`.

## Exact repro
    python3 -c "
    from personal_index.rss import Feed, FeedEntry
    f = Feed(entries=[FeedEntry(title=str(i)) for i in range(5)])
    print('count=0  ->', [e.title for e in f.get_recent_entries(0)])
    print('count=-1 ->', [e.title for e in f.get_recent_entries(-1)])
    print('count=2  ->', [e.title for e in f.get_recent_entries(2)])
    "

## Observed output
    count=0  -> []
    count=-1 -> ['0', '1', '2', '3']
    count=2  -> ['0', '1']

## Expected per docs
    count=0  -> []
    count=-1 -> []
    count=2  -> ['0', '1']

A negative `count` is out-of-range and must return an empty list, consistent
with the `count=0` guard. The `self.entries[:count]` slice leaks Python
negative-slice semantics (all-but-last) for `count=-1`.

## Deep test
tests/deep/test_rss_adversarial.py::test_get_recent_entries_negative_count_returns_empty
(xfail-strict; will flip to a hard pass once the guard is added).
