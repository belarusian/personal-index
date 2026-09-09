# ARCH-62 — link_analyzer: negative `max_anchor_length` clamp contract (0-path yields `{'': 1}`)

Status: OPEN
Component: `personal_index/link_analyzer.py` — `LinkAnalyzer.__init__`, `LinkAnalyzer._analyze_single_link`
Umbrella: ARCH-2 (#983)
Issue: #1206
Docs: `docs/link-analyzer.md` (Contract Holes)
Resolves: IMPL-5 (pushback on QA-9, Issue #1165)

## Problem
`LinkAnalyzer.__init__(max_anchor_length=...)` does not guard a negative bound.
In `_analyze_single_link`, anchor text is truncated with
`a[:self.max_anchor_length]`. A negative N is a Python negative slice that
**drops the last N characters** instead of clamping to a non-negative bound:

- `max_anchor_length=-1`, anchor `"hello"` -> `"hell"` (last char dropped).
- `max_anchor_length=-2`, anchor `"hello world"` -> `"hello wor"` (last 2 dropped).

A negative bound is a caller error that should behave like `0`. Instead it
silently corrupts the anchor text that feeds `stats.anchor_text_distribution`
and `top_anchor_texts`.

QA-9 (Issue #1165) mandated a single-line clamp in `__init__`:
    self.max_anchor_length = max(0, self.max_anchor_length)
and stated that BOTH xfail-strict tests in
`tests/deep/test_link_analyzer_adversarial.py::TestNegativeMaxAnchorLength`
"flip to hard passes" from that clamp alone. QA-9 also explicitly FORBIDS
changing the counting idiom: "Do NOT change the `a[:self.max_anchor_length]`
idiom itself."

The cycle-211 implementer (IMPL-5) pushed back: applying exactly that clamp
gives
    test_negative_max_anchor_length_clamped    XFAIL (still)
    test_negative_max_anchor_length_matches_zero FAILED (XPASS strict)
because the two tests are mutually inconsistent with the actual 0-path
behaviour. IMPL-5 is OPEN; the implementer will not guess.

## Architect Decision (cycle 226)

**Decision: option (a) — the 0-path yields `{'': 1}` (an empty anchor IS
counted). The clamp-only fix in `__init__` is the complete,
contract-consistent fix, and the counting idiom is NOT changed.**

Rationale (recorded verbatim):
1. It keeps the ticket's explicit "do not change the `a[:self.max_anchor_length]`
   idiom" restriction intact — the clamp in `__init__` is the only code change,
   which is the minimal, contract-consistent fix.
2. It matches the ACTUAL 0-path behaviour (`{'': 1}`), so the contract documents
   what the code really does rather than an aspirational `{}`.
3. It makes `test_negative_max_anchor_length_matches_zero` a hard pass (the
   clamp makes -2 behave like 0 → both `{'': 1}` → equal).
4. It resolves `test_negative_max_anchor_length_clamped` by CORRECTING the
   ticket's wrong Observed line and re-pinning that test to expect `{'': 1}`
   (or dropping it, since `matches_zero` already pins the clamp). This is a
   test-pinning correction, NOT a code change — it belongs to the implementer /
   a status pass, NOT this pass.
5. It REJECTS option (b) "skip empty truncations (guard on the truncated
   value)": that requires editing the counting idiom in `_analyze_single_link`,
   which QA-9 explicitly forbids, and it would change the 0-path meaning (empty
   anchor no longer counted) — a larger, contract-changing fix the ticket does
   not ask for.

**Why the 0-path yields `{'': 1}` (not `{}`):** in `_analyze_single_link` the
code is
    a = anchor.strip()
    if a:
        anchor_counter[a[:self.max_anchor_length]] += 1
The guard is on the **stripped, pre-truncation** anchor `a`. For anchor
`"hello"` and `max_anchor_length=0`, `a` is non-empty so the guard passes and
`anchor_counter[a[:0]] += 1 == anchor_counter[''] += 1`. The distribution is
`{'': 1}`, not `{}`. Direct repro on origin/main (no fix applied):
    LinkAnalyzer(base_domain='example.com', max_anchor_length=0).analyze(
        'http://example.com/', [{'url':'http://ext.com/x','text':'hello'}]
    ).stats.anchor_text_distribution  ->  {'': 1}
So QA-9's own Observed line "max_anchor_length=0 : {}" is factually wrong, and
`test_negative_max_anchor_length_clamped` cannot pass from the clamp alone.

**IMPL-5 resolution:** the architect picks option (a). The clamp-only fix is
the complete fix; the counting idiom is NOT changed. The two xfail-strict tests
are corrected to hard passes (see "Pinning tests to add" below). IMPL-5 is
resolved by this decision.

**Downstream status effect (for the implementer, not edited here):** QA-9
leaves OPEN-PUSHBACK and IMPL-5 is resolved by this decision; the implementer
proceeds per this section + "Public contract (target)".

## Public contract (target)
- `LinkAnalyzer.__init__`: clamp the stored bound to a non-negative floor —
    self.max_anchor_length = max(0, max_anchor_length)
  This is the ONLY code change. A negative `max_anchor_length` is clamped to
  `0` and behaves identically to `0`.
- `_analyze_single_link`: the counting idiom is UNCHANGED —
    a = anchor.strip()
    if a:
        anchor_counter[a[:self.max_anchor_length]] += 1
  The guard stays on the stripped, pre-truncation anchor `a`. Do NOT change it
  to guard on the truncated value.

## Behavior
- `max_anchor_length=-1` (clamped to 0), anchor `"hello"` ->
  `anchor_text_distribution == {'': 1}` (identical to `max_anchor_length=0`).
- `max_anchor_length=-2` (clamped to 0), anchor `"hello world"` ->
  `anchor_text_distribution == {'': 1}` (identical to `max_anchor_length=0`).
- `max_anchor_length=0`, anchor `"hello"` -> `anchor_text_distribution ==
  {'': 1}` (an empty anchor IS counted — the guard is on the pre-truncation
  anchor, not the truncated value).
- `max_anchor_length=100` (default), anchor `"hello"` ->
  `anchor_text_distribution == {'hello': 1}` (unchanged).
- A link whose anchor is empty/whitespace-only (`a` is empty after
  `strip()`) is NOT counted at all (the guard fails) — unchanged.

## Guard inputs
- `max_anchor_length=-1` (negative) — clamped to 0; behaves like 0.
- `max_anchor_length=0` — the 0-path; a non-empty anchor is truncated to `''`
  and counted as `''` (`{'': 1}`).
- `max_anchor_length=-100` (large negative) — clamped to 0; behaves like 0.
- An empty/whitespace-only anchor with any `max_anchor_length` — not counted
  (guard on `a` fails).

## Acceptance criteria
1. `LinkAnalyzer(base_domain='example.com', max_anchor_length=-1).analyze(
   'http://example.com/', [{'url':'http://ext.com/x','text':'hello'}])
   .stats.anchor_text_distribution == {'': 1}` (clamped to 0, empty anchor
   counted).
2. `LinkAnalyzer(base_domain='example.com', max_anchor_length=-2).analyze(
   'http://example.com/', [{'url':'http://ext.com/x','text':'hello world'}])
   .stats.anchor_text_distribution == {'': 1}` (clamped to 0).
3. The `max_anchor_length=-2` result equals the `max_anchor_length=0` result
   for the same links (both `{'': 1}`).
4. `max_anchor_length=100` (default) is unchanged: anchor `"hello"` ->
   `{'hello': 1}`.
5. An empty/whitespace-only anchor is not counted for any `max_anchor_length`.
6. The counting idiom in `_analyze_single_link` is UNCHANGED (the guard stays
   on the stripped, pre-truncation anchor `a`; the `a[:self.max_anchor_length]`
   idiom is intact).

## Pinning tests to add
The 2 existing xfail-strict tests in
`tests/deep/test_link_analyzer_adversarial.py::TestNegativeMaxAnchorLength`
are corrected to hard passes (remove the `@pytest.mark.xfail(strict=True, ...)`
decorator) — this is a test-pinning correction, NOT a code change:
- `test_negative_max_anchor_length_clamped`: re-pin the assertion to expect
  `{'': 1}` (NOT `{}`) — the 0-path counts the empty anchor. (Alternatively
  drop it, since `matches_zero` already pins the clamp; the architect prefers
  re-pinning so the 0-path `{'': 1}` is witnessed directly.)
- `test_negative_max_anchor_length_matches_zero`: unchanged assertion (the
  -2 result equals the 0 result); it becomes a hard pass from the clamp alone.
Both tests pin the clamp AND the 0-path `{'': 1}` behaviour against the
returned object.

## Docs update (same PR)
`docs/link-analyzer.md` — the `max_anchor_length` Contract-Holes bullet is
corrected: it currently claims a non-positive value "silently truncates every
anchor to the empty string ... so `anchor_text_distribution` ends up empty",
which conflates `anchor[:0]` (empty) with `anchor[:-1]` (drops last char) and
is factually wrong (the 0-path yields `{'': 1}`, not `{}`). The bullet is
marked DECIDED (cycle 226) with a pointer to `tickets/ARCH-62.md`, and the
`analyze` / `LinkAnalyzer` entries state the resolved contract: a negative
`max_anchor_length` is clamped to 0 in `__init__` and behaves like 0 (a
non-empty anchor is truncated to `''` and counted as `''`, so
`anchor_text_distribution == {'': 1}`); the counting idiom is unchanged.
