# TICKET-100: Misleading `.strip()` with multi-character string in `url_dedup.py` (B005)

## Title
`domain.lower().lstrip("www.")` uses `lstrip` with a multi-character string, which strips individual characters not the substring

## Evidence
`personal_index/url_dedup.py:213`:
