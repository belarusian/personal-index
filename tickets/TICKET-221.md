# TICKET-221: Functions exceeding 150 lines

## Evidence
- `personal_index/docs_generator.py`: `generate_dashboard()` spans 590 lines
- `personal_index/cli_verify.py`: `verify()` spans 190 lines

## Impact
- Difficult to read, test, and maintain
- Violates single responsibility principle
- Hard to identify which parts to modify

## Suggestion
- docs_generator.py: Split generate_dashboard into per-section functions
- cli_verify.py: Extract verification steps into separate functions
