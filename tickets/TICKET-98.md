# TICKET-98: Duplicate set item `"wrong"` in `content_enricher.py` (B033)

## Title
`SentimentAnalyzer.NEGATIVE_WORDS` set contains the duplicate item `"wrong"`

## Evidence
`personal_index/content_enricher.py:66` — the `NEGATIVE_WORDS` set literal contains `"wrong"` twice:
