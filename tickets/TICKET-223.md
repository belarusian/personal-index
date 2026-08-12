# TICKET-223: Bare except Exception in pipeline.py

## Evidence
- `personal_index/pipeline.py`, line 138: `except Exception:` in PipelineStep.run()
- Catches all exceptions without logging or specific handling
- Only differentiates between "continue"/"skip" vs re-raise

## Impact
- Swallows errors silently when on_error is "continue" or "skip"
- No logging of what failed, making debugging difficult
- Could mask critical errors (KeyboardInterrupt, SystemExit)

## Suggestion
Add logging of the caught exception. Consider catching specific exceptions instead.
