# TICKET-63: Missing `raise ... from err` in exception chains (B904)

## Title
Exception chains lose original traceback — `raise ... from err` or `raise ... from None` should be used in except clauses

## Evidence
ruff B904 flags 3 locations where exceptions are re-raised without preserving the original traceback:

1. `personal_index/api/server.py:40` — ImportError re-raised without `from`
2. `personal_index/serializer.py:54` — SerializationError re-raised without `from`
3. `personal_index/serializer.py:61` — DeserializationError re-raised without `from`

Example from `personal_index/serializer.py:53-54`:
