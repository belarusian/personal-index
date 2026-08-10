# TICKET-104: Broad `except Exception` catches in 6 locations across 4 modules

## Title
Six `except Exception` clauses catch overly broad exception types, masking potential bugs

## Evidence
The following locations use `except Exception` where more specific exception handling would be appropriate:

1. **`personal_index/pipeline.py:27`** — catches `Exception` in `PipelineStep.execute()`:
