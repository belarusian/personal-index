# TICKET-230: Refactor `verify` in cli_verify.py (77L → ≤50L)

## What's Wrong

`personal_index/cli_verify.py:verify` (line 217, 77 lines) exceeds the 50-line function limit. It bundles check orchestration, cleanup, and summary reporting into one function.

## Evidence

Reading lines 217–293 of `personal_index/cli_verify.py`:

1. **Nested `check` helper** (lines 233–241): A closure that manages `checks_passed`/`checks_total` counters and prints pass/fail. This is a self-contained utility.
2. **Sequential check calls** (lines 244–268): Six calls to `_check_*` functions, each followed by a `check()` call. This is a linear pipeline of 12 lines of repetitive pattern.
3. **Cleanup** (lines 271–275): Removes temporary verify files from the data directory.
4. **Summary reporting** (lines 278–287): Prints results header, failed checks, or success message.

The six check invocations follow an identical pattern:
