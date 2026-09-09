Status: OPEN
Kind: IMPL
Ref: QA-10 (Issue #1166)

# IMPL-6: QA-10 mandated formula contradicts the ticket's stated intent and a pinned test

## Blocking sentences (quoted verbatim from tickets/QA-10.md)
"The unique_external_domains field must reflect the true number of distinct
external domains across the analyzed pages (consistent with the per-page
stats.unique_domains), not the top-20 truncated window."

and

"(2 xfail-strict tests pin the correct contract; they flip to hard passes once
the implementer derives the unique-domain count from the full counter rather
than the top-20 domain_distribution)."

## Why this is infeasible as written
The cycle-212 briefing pins the acceptance-exact fix to the formula:
    total_unique_domains = sum(r.stats.unique_domains for r in results)
    "unique_external_domains": total_unique_domains

That formula SUMS the per-page distinct counts. It is a per-page sum, not a
cross-page set-union, so a domain that appears on more than one page is
counted once per page. It therefore contradicts the ticket's own stated intent
("the true number of distinct external domains across the analyzed pages") and
breaks a pre-existing, currently-passing, non-xfail validator-pinned test.

Direct repro on origin/main (no fix applied):
    pages = [
        {"url": "http://example.com/1", "links": [
            {"url": "http://example.com/a", "text": "i"},
            {"url": "http://a.com/x", "text": "e"}]},
        {"url": "http://example.com/2", "links": [
            {"url": "http://b.com/x", "text": "e"},
            {"url": "http://a.com/y", "text": "e"}]},
    ]
    results = analyzer.analyze_batch(pages)
    agg = analyzer.get_aggregate_stats(results)
    # a.com on BOTH pages, b.com on page 2 -> true distinct across pages = 2

With the mandated formula:
    per-page stats.unique_domains = [1, 2]   (a.com on p1; a.com+b.com on p2)
    sum(...) = 3
    agg["unique_external_domains"] = 3

But tests/deep/test_link_analyzer_adversarial.py::TestBatchAndAggregate::
test_aggregate_sums (a live, non-xfail pinned contract, currently green on
origin/main) asserts:
    assert agg["unique_external_domains"] == 2

So the mandated formula makes that pinned test FAIL (3 != 2). The two QA-10
xfail-strict tests each use a SINGLE page (25 and 50 domains on one page), so
for a single page sum(...) == the per-page count and they pass; the conflict
only surfaces with 2+ pages, which test_aggregate_sums exercises.

## The deeper design gap
The ticket's stated intent (a cross-page set-union of distinct external
domains) is NOT computable from the per-page stats as currently stored.
LinkAnalysisResult.stats exposes only:
    unique_domains: int            (full per-page distinct count)
    domain_distribution: dict      (top-20 truncated)
The full per-page domain Counter is not exposed, so neither the mandated
sum-of-counts nor a true cross-page set-union can be derived from r.stats
alone without either (a) exposing the full per-page domain set, or (b)
accepting the sum-of-counts semantics (which double-counts across pages).

## Architect decision required (pick one)
(a) Keep the mandated sum-of-counts formula AND re-pin
    test_aggregate_sums to expect 3 (documenting that
    unique_external_domains is a per-page sum, not a cross-page distinct
    count). This changes the meaning of the field and the pinned contract.
(b) Change the field's contract to a true cross-page distinct count and expose
    the full per-page domain set (e.g. stats.external_domains: set[str]) so
    get_aggregate_stats can union across pages; re-pin the 2 QA-10 tests and
    keep test_aggregate_sums at 2.
(c) Correct the ticket's stated intent to match the sum-of-counts semantics
    and update test_aggregate_sums accordingly.

The implementer will not guess between these; QA-10 is set OPEN-PUSHBACK.
