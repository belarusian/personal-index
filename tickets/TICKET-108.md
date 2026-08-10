# TICKET-108: Code quality — Duplicate `os.makedirs` call in `interests.py`

## Title
`personal_index/interests.py` calls `os.makedirs` twice with identical arguments

## Evidence
File: `personal_index/interests.py`, lines 56-62
