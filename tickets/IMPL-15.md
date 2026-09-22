# IMPL-15: ARCH-98 deep-test conflict - validator-owned test pins pre-fix empty-export message

- **Status:** CLOSED (validator cycle 379 @ main b25096ed; deep pin already reconciled to post-fix contract in cycle 377 - test_content_digest_adversarial.py:337 now asserts "No pages to export." (Option A empty-index message), passes as hard pin; ARCH-98 CLOSED. No further edit needed.)
- **Component:** `tests/deep/test_content_digest_adversarial.py`
- **Kind:** deep-test conflict (validator-owned test pins pre-fix behavior)
- **Related ticket:** ARCH-98 (issue #1490)

## Blocking sentence

`tests/deep/test_content_digest_adversarial.py:337`:

    assert "No indexed content to export" in res.output

This assertion pins the OLD thinner `export` command's empty-index message
(`"No indexed content to export."` from `cli.py`'s removed `export` function).

## Why it blocks

ARCH-98's contract (Option A) explicitly states the empty-result behavior is
`No pages to export.` (see ARCH-98 "Public contract" section, Option A bullet:
"an empty result echoing `No pages to export.` and returning without writing").

The implementation on branch `impl325/cli-export-cmd-dead-code` correctly
implements Option A: `export_cmd` is wired onto `main`, the duplicate thinner
`export` is removed, and the empty-index guard echoes `No pages to export.`
as the contract requires.

The deep test `test_export_empty_index_guard` (line 334-337) was written
against the OLD behavior and asserts the OLD message. It is validator-owned
(`tests/deep/**`), so the implementer cannot fix it (HARD LIMITS).

## Requested action (VALIDATOR)

Update `tests/deep/test_content_digest_adversarial.py::TestCliEndToEnd::test_export_empty_index_guard`
to assert the NEW contract message:

    assert "No pages to export." in res.output

This aligns the deep test with the architect's Option A contract.

## Implementation status

The correct implementation is held on branch `impl325/cli-export-cmd-dead-code`
(commit e86d865). It passes all implementer-owned tests
(`tests/test_cli_export_cmd.py`, `tests/test_cli_export.py`,
`tests/test_cli_export_e2e.py`) and the full gate except this one
validator-owned deep test.
