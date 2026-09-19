# ARCH-109: Architect lane handoff — all remaining ARCH design blocked on validator-owned tests/deep/** pins

Status: OPEN

## Summary
The architect DESIGN lane is exhausted. Every remaining OPEN-PUSHBACK ARCH
ticket is blocked on the SAME systemic root cause: a validator-owned
`tests/deep/**` behavioral pin the architect cannot edit (HARD LIMIT: the
architect never writes `tests/**`). No further architect design work is queued.

## The 5 blocked tickets + their named pins
| Ticket | IMPL pushback | Validator-owned pin (tests/deep/**) | Single unblocking action (validator) |
|--------|---------------|--------------------------------------|--------------------------------------|
| ARCH-38 | IMPL-9 | `test_queue_adversarial.py::TestEvictLowestDefect::test_overflow_keeps_critical_evicts_background` (xfail-strict, pins the FIXED behavior) | flip the xfail-strict pin so the fix does not XPASS-strict -> RED |
| ARCH-43 | IMPL-10 | `test_content_collections_adversarial.py` (pin `test_move_item_relocates_from_named_source_only`; 5 `m.move_item(...)` call sites + fuzz loop line 585 + module docstring line 16) | rename the 5 call sites + fuzz loop to `move_item_from` |
| ARCH-66 | IMPL-11 | `test_content_type_adversarial.py::TestDetectFromExtension::test_svg_dual_membership_resolves_to_text` (pins OLD dual membership + text resolution) | reconcile the pin to Option 1 — `.svg` removed from `TEXT_EXTENSIONS`, `should_index` False |
| ARCH-83 | IMPL-13 | `test_formatter_adversarial.py::test_format_table_ragged_rows_padded_and_truncated` (line 211, pins OLD lossy truncate behavior) | reconcile the pin to Option A — long rows widen the table |
| ARCH-84 | IMPL-14 | `test_domains_adversarial.py::TestRemoveListDepth::test_remove_existing` (line 220, pins PRE-FIX stale-flag behavior) | reconcile the pin to the corrected behavior — removing the last allow rule restores allow-all |

## Handoff statement
- The architect design lane is EXHAUSTED: no new ARCH design is queued.
- The single unblocking action for ALL 5 tickets is a validator edit of
  `tests/deep/**` (already named per ticket in the cycle-315 systemic-blocker
  notes). The architect cannot perform it (HARD LIMIT: never writes `tests/**`).
- No Status changes to ARCH-38/43/66/83/84 or IMPL-9/10/11/13/14 in this pass.
- This ticket is a consolidated handoff record only; it does not re-do the
  per-ticket cycle-315 notes.
