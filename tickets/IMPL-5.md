Status: CLOSED (resolved by ARCH-62, cycle 226; QA-9 #1165 remains OPEN-PUSHBACK until the implementer lands the clamp fix)
Kind: IMPL
Ref: QA-9 (Issue #1165)

# IMPL-5: QA-9 acceptance criteria infeasible with the mandated clamp-only fix

## Blocking sentence (quoted verbatim from tickets/QA-9.md)
"2 xfail-strict tests pin the correct contract; they flip to hard passes once
the implementer clamps `max_anchor_length = max(0, max_anchor_length)`."

and the ticket's Observed output line:
"max_anchor_length=0   : {}"

## Why this is infeasible as written
The ticket mandates a single-line clamp in LinkAnalyzer.__init__
(self.max_anchor_length = max(0, max_anchor_length)) and states that BOTH
xfail-strict tests in tests/deep/test_link_analyzer_adversarial.py::
TestNegativeMaxAnchorLength "flip to hard passes" from that clamp alone.

Applying exactly that clamp and running the class gives:
  test_negative_max_anchor_length_clamped    XFAIL  (still)
  test_negative_max_anchor_length_matches_zero FAILED (XPASS strict)

The two tests are mutually inconsistent with the actual 0-path behaviour:

- test_negative_max_anchor_length_matches_zero compares the -2 result to the
  0 result. With the clamp both yield {'': 1}, so they are equal and the test
  passes (XPASS strict -> FAILED). This test is satisfiable by the clamp.

- test_negative_max_anchor_length_clamped asserts, for max_anchor_length=-1
  (clamped to 0), that r.stats.anchor_text_distribution == {}. But the 0-path
  does NOT yield {}. In _analyze_single_link the code is:
      a = anchor.strip()
      if a:
          anchor_counter[a[:self.max_anchor_length]] += 1
  For anchor "hello" and max_anchor_length=0, a is non-empty so the guard
  passes and anchor_counter[a[:0]] += 1 == anchor_counter[''] += 1. The
  distribution is {'': 1}, not {}.

  Direct repro on origin/main (no fix applied):
      LinkAnalyzer(base_domain='example.com', max_anchor_length=0).analyze(
          'http://example.com/', [{'url':'http://ext.com/x','text':'hello'}]
      ).stats.anchor_text_distribution  ->  {'': 1}

  So the ticket's own Observed output line "max_anchor_length=0   : {}" is
  factually wrong, and test_negative_max_anchor_length_clamped cannot pass
  from the clamp alone.

## The only way to make test 1 pass is forbidden by the ticket
To make the 0-path yield {} (skip counting an empty truncation) the code must
change the counting idiom, e.g. guard on the truncated value:
      t = a[:self.max_anchor_length]
      if t:
          anchor_counter[t] += 1
The ticket explicitly forbids this: "Do NOT change the `a[:self.max_anchor_length]`
idiom itself - clamping the stored value is the contract-consistent fix."

## What the architect must decide (in docs/)
One of:
  (a) Correct the contract: the 0-path yields {'': 1} (empty anchor counted),
      and re-pin test_negative_max_anchor_length_clamped to expect {'': 1}
      (or drop it, since matches_zero already pins the clamp). Then the
      clamp-only fix is complete and both tests are consistent.
  (b) Change the contract so an empty truncation is NOT counted (skip it),
      which requires editing the counting idiom in _analyze_single_link -
      i.e. lift the "do not change the idiom" restriction. Then the clamp +
      idiom guard make both tests pass as written.

Until resolved, QA-9 is set to OPEN-PUSHBACK. The implementer will not guess
between (a) and (b).
