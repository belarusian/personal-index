Status: CLAIMED 2026-09-06
Kind: QA
Issue: #1134
Deep test: tests/deep/test_negslice_sweep2_adversarial.py (8 xfail-strict + 2 clean armor)

# QA-5: negative-slice "top N / limit" leak - SECOND class sweep (9 new sites missed by QA-4)

## Symptom
The negative-slice "top N / limit" defect class (QA-1 `extract_top_n`, QA-2
`tfidf`/`index.search`, QA-3 `Feed.get_recent_entries`, QA-4 sweep of 13 sites -
all now CLOSED) is not fully swept. A whole-codebase re-sweep of the slicing
idiom (`grep -rnE '\[:[a-z_]+\]' personal_index/`) found **9 FURTHER public
"top N / limit" functions** that leak Python negative-slice semantics: a
negative bound returns `list[:-1]` (all-but-last) instead of an empty list,
while the `0` guard correctly returns `[]`. Out-of-range (negative) N must yield
an empty list, matching the zero guard.

These 9 sites were NOT in the QA-4 sweep table and still leak at HEAD.

## Affected sites (9, all confirmed leaking)
| # | module | function | line | idiom |
|---|--------|----------|------|-------|
| 1 | content_categorizer.py | `CategorizationResult.top_n(n)` | 257 | `self.topics[:n]` |
| 2 | content_linker/similarity.py | `SimilarityEngine.find_similar(limit)` | 86 | `results[:limit]` |
| 3 | search_facets/facet_builder.py | `FacetBuilder.build(max_values)` | 63 | `facet.values[:max_values]` |
| 4 | content_digest.py | `DigestGenerator.generate(max_entries_per_section)` | 201/224/231/250 | `entries[:max_per_section]` |
| 5 | formatter.py | `format_search_results(limit)` | 22 | `results[:limit]` |
| 6 | content_export_csv.py | `CSVExporter.export(limit)` | 87 | `filtered[:limit]` |
| 7 | cli.py | `list_pages` (CLI `list --limit`) | 878 | `_sort_pages(...)[:limit]` |
| 8 | cli.py | `top` (CLI `top --limit`) | 905 | `sorted(...)[:limit]` |
| 9 | cli_top.py | `top_pages` (CLI `top` alt impl) | 23 | `index.list_pages()[:limit]` |

Note: site 9 (`cli_top.py`) is a standalone `@click.command("top")` that is not
currently wired into the main CLI (the live `top` is `cli.py:905`), but it is a
public module with the same leak and should be guarded for consistency.

## Exact repro (site 1 - content_categorizer.top_n)
    python3 -c "
    from personal_index.content_categorizer import CategorizationResult, TopicScore
    r = CategorizationResult(primary_topic='a', topics=[
        TopicScore(topic='a', score=5), TopicScore(topic='b', score=3),
        TopicScore(topic='c', score=1)])
    print('top_n(-1) ->', len(r.top_n(-1)))
    print('top_n(0)  ->', len(r.top_n(0)))
    print('top_n(2)  ->', len(r.top_n(2)))
    "

## Observed output (site 1)
    top_n(-1) -> 2
    top_n(0)  -> 0
    top_n(2)  -> 2

`top_n(-1)` returns 2 of 3 (all-but-last) instead of 0.

## Exact repro (site 7/8 - CLI end-to-end)
    python3 -c "
    import os, tempfile
    from click.testing import CliRunner
    from personal_index.cli import main
    from personal_index.index import SearchIndex
    from personal_index.models import CrawledPage
    dd = tempfile.mkdtemp()
    idx = SearchIndex(db_path=os.path.join(dd, 'search_index.json'))
    for i in range(3):
        idx.add_page(CrawledPage(url=f'http://x{i}', title=f't{i}', content='c'))
    r = CliRunner().invoke(main, ['list', '--limit', '-1', '--data-dir', dd])
    print('list --limit -1 ->', r.output.count('http://'), 'pages (should be 0)')
    r0 = CliRunner().invoke(main, ['list', '--limit', '0', '--data-dir', dd])
    print('list --limit 0  ->', r0.output.count('http://'), 'pages')
    rt = CliRunner().invoke(main, ['top', '--limit', '-1', '--data-dir', dd])
    print('top  --limit -1 ->', rt.output.count('http://'), 'pages (should be 0)')
    "

## Observed output (CLI)
    list --limit -1 -> 2 pages (should be 0)
    list --limit 0  -> 0 pages
    top  --limit -1 -> 2 pages (should be 0)

## Expected per docs
Each function's docstring/contract states a "top N" / "limit" / "max" bound.
A negative bound is out-of-range and must yield an empty result, consistent with
the `0` guard. Fix: add `if N <= 0: return []` (or clamp to `max(0, N)`) before
the slice, and state the guard in the docstring.

## Deep test
tests/deep/test_negslice_sweep2_adversarial.py
- 8 xfail-strict tests (one per leaking site, sites 1-8; site 9 covered by the
  same idiom) pin the CORRECT contract (negative -> empty) and XFAIL while the
  leak exists. Each flips to a hard pass once the guard is added (remove the
  xfail marker).
- 2 clean armor tests (CLI `list --limit 0` and `--limit 2`) already pass.

## Acceptance
- Each of the 9 sites returns an empty result for N <= 0 and is unchanged for
  N > 0; docstring states the guard.
- All 8 xfail-strict tests flip to hard passes (markers removed).
