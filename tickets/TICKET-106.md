# TICKET-106: Mypy type error — BeautifulSoup AttributeValueList type mismatches

## Title
Multiple modules have type errors with BeautifulSoup's `AttributeValueList`

## Evidence
Files with type errors (mypy union-attr):
- `personal_index/content_extractor.py` (lines 74, 84, 91, 98, 105, 114, 122, 131-132)
- `personal_index/content.py` (lines 74, 81, 104, 106, 114)
- `personal_index/utils/__init__.py` (lines 28, 32, 52)
- `personal_index/crawler/__init__.py` (lines 123, 126, 149)

Example from `content_extractor.py`:
