# TICKET-54: Type error — scraper.py, link_preview.py, importer.py, content_extractor.py handle AttributeValueList incorrectly

## Title
BeautifulSoup attribute access returns `str | AttributeValueList`, but code assumes `str`

## Evidence
Multiple modules call `.get()` on BeautifulSoup elements and assume the result is `str`, but BeautifulSoup returns `AttributeValueList` when an attribute has multiple values.

Affected files and lines:
- `personal_index/scraper.py:89,92,108,112,116,120,138,157`
- `personal_index/link_preview.py:100,107,114`
- `personal_index/importer.py:162,163`
- `personal_index/content_extractor.py:75,85,92`
- `personal_index/url_utils.py:339`

Example from `personal_index/scraper.py:89`:
