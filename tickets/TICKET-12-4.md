# TICKET-12-4: Refactor `publish_dashboard.main` (55L, line 177)

## What's wrong

`main()` in `personal_index/publish_dashboard.py` (line 177) is 55 lines and handles three distinct concerns:
1. **Argument parsing** — 30 lines of `argparse.ArgumentParser` configuration (lines 178–206)
2. **Dashboard path resolution** — conditional logic for `--regenerate` vs existing files with existence checks (lines 208–224)
3. **Sync validation + interactive prompt** — validation, warning, and user confirmation (lines 227–237)

The argument parser construction is the single largest block and is completely independent of the execution logic.

## Evidence
