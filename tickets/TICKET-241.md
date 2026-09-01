# TICKET-241: Extract duplicated file-import logic from `cli.watch`

## Title
`cli.watch` (L1312, 75 lines) contains near-identical file-import blocks for single-file and directory modes — extract a shared `_index_file` helper

## Evidence
`personal_index/cli.py`, lines 1312–1386. The once-mode section has two nearly identical blocks:

**Single-file import (L1338–1356):**

## Status: RESOLVED (verified against code, cycle 1)
