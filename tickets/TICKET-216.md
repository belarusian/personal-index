# TICKET-216: Missing tests for live modules

## Evidence
- `personal_index/__init__.py`: No tests/test___init__.py (but __init__ is just exports — low priority)
- `personal_index/__main__.py`: No tests/test___main__.py (entry point — low priority)
- `personal_index/cli_top.py`: No tests/test_cli_top.py (CLI command — should have tests)
- `personal_index/cli_verify.py`: No tests/test_cli_verify.py (CLI command — should have tests)
- `personal_index/pipeline_runner.py`: No tests/test_pipeline_runner.py (core module — HIGH priority)

## Impact
- Untested code paths may regress silently
- pipeline_runner is a core orchestration module without any test coverage

## Suggestion
Add unit tests for cli_top, cli_verify, and especially pipeline_runner.
