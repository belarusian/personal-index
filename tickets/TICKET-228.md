# TICKET-228: docs_generator.py has 8 mypy errors — root cause audit

## What's wrong

`personal_index/docs_generator.py` (1355 lines) has 8 mypy errors across 5 lines.
Two distinct root causes: untyped dict lambdas and an untyped internal function.

## Evidence
