# TICKET-59: Misleading .lstrip("www.") in url_dedup.py — strips individual characters, not substring

## Title
url_dedup.py uses .lstrip("www.") which strips individual characters, not the substring "www."

## Evidence
`personal_index/url_dedup.py:213`:
