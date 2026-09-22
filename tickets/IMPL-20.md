# IMPL-20: ARCH-98 deep-test conflict - six validator-owned tests pin the pre-fix empty-export message

- **Status:** OPEN
- **Component:** tests/deep/** (six validator-owned files)
- **Kind:** deep-test conflict (validator-owned tests pin pre-fix behavior)
- **Related ticket:** ARCH-98 (issue #1490)

## Blocking sentence

ARCH-98 Option A (confirmed by the architect, cycle 298) requires the
reachable `personal-index export` to echo `No pages to export.` on an empty
result. Six validator-owned deep tests invoke the reachable `export` against an
empty index and assert the OLD thinner `export` command's message
(`No indexed content to export.`), so the correct Option A implementation
fails the local gate on exactly these six tests:

- tests/deep/test_url_filter_adversarial.py:325
  assert "No indexed content to export." in r.output
- tests/deep/test_url_filter_deep_adversarial.py:342
  assert "No indexed content to export." in r.output
- tests/deep/test_serializer_adversarial.py:352
  assert "No indexed content to export." in r.output
- tests/deep/test_validator_url_adversarial.py:341
  assert "No indexed content to export." in r.output
- tests/deep/test_url_dedup_adversarial.py:242
  assert "No indexed content to export." in r.output
- tests/deep/test_content_export_csv_adversarial.py:253
  assert "No indexed content" in result.output

## Why it blocks

The correct Option A implementation (held on branch
impl358/arch98-wire-export-cmd, commit 0c7f1412) wires
`cli_export.export_cmd` onto the `main` group and deletes cli.py's duplicate
thinner `export`. The reachable `export` then echoes `No pages to export.` on
an empty index, as the contract requires. The six deep tests above still pin
the OLD message, so they FAIL on the implementation branch:

  6 failed, 12612 passed, 22 skipped, 1 xfailed, 5 xpassed

These tests are validator-owned (tests/deep/**), so the implementer lane cannot
edit them (HARD LIMITS).

## Note on the cycle-333 deadlock-break

Cycle 333 reconciled ONE of these deep tests
(tests/deep/test_content_digest_adversarial.py::TestCliEndToEnd::test_export_empty_index_guard,
now xfail(strict=False) asserting the NEW message). The other six were not
reconciled, so the conflict persists.

## Requested action (VALIDATOR)

Update the six deep tests above to assert the NEW Option A contract message:

    assert "No pages to export." in r.output

(or, for the content_export_csv test, `assert "No pages to export." in
result.output`). This aligns the deep tests with the architect's Option A
contract and unblocks the ARCH-98 implementation.

## Implementation status

The correct implementation is held on branch
impl358/arch98-wire-export-cmd (commit 0c7f1412). It passes all
implementer-owned tests (tests/test_cli_export_cmd.py, tests/test_cli_export.py,
tests/test_cli_export_e2e.py, and the updated my-path export tests) and the
full gate EXCEPT the six validator-owned deep tests named above.
