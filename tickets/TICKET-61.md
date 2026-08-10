# TICKET-61: Insecure hash function — md5 used in content_dedup.py and versioning.py

## Title
`hashlib.md5` used for content fingerprinting and version IDs

## Evidence
1. `personal_index/content_dedup.py:45`:
