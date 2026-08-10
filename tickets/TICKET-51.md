# TICKET-51: Type error — backup.py tarfile.open() called with wrong mode argument

## Title
`tarfile.open()` called with positional mode argument instead of keyword argument, causing type errors

## Evidence
`personal_index/backup.py:90`:
