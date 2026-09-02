# TICKET-260: content_merger.py - non-string tag element crashes all merge strategies

## File
personal_index/content_merger.py

## Symptom
All four merge methods (_merge_concatenate, _merge_longest, _merge_highest_priority,
_merge_unique_paragraphs) call t.lower() on elements of source.tags without an
isinstance(t, str) type guard. If a non-string element (int, None, etc.) is present in
the tags list, the entire merge operation crashes with AttributeError, aborting the
content pipeline.

## Evidence
- Line 106: all_tags.update(t.lower() for t in source.tags) in _merge_concatenate
- Line 127: same in _merge_longest
- Line 145: same in _merge_highest_priority
- Line 172: same in _merge_unique_paragraphs
- MergeSource dataclass has NO __post_init__ to filter/coerce non-string elements.
- Reproduced: MergeSource(url=x, tags=[1, valid, None]) -> AttributeError in all 4 strategies.

## Minimal Additive Fix
Guard each t.lower() call with isinstance(t, str), consistent with the existing pattern
in models.py (TICKET-259) and interests.py. Change the generator expression to filter
with if isinstance(t, str) in all four merge methods.

Issue: #349

## Status
RESOLVED (merged to main, gh #349 closed)
