Status: OPEN
Kind: QA
Issue: #1047
Deep test: tests/deep/test_progress_adversarial.py::test_list_completed_negative_limit_returns_empty (xfail-strict)

# QA-4: negative-slice "top N / recent N" leak - CLASS SWEEP across the whole codebase (13 new sites)

## Symptom
The negative-slice "top N / recent N" defect class (QA-1 `extract_top_n`,
QA-2 `tfidf.rank_documents`/`get_top_terms` + `index.py SearchIndex.search`,
QA-3 `Feed.get_recent_entries`) is not isolated to those three sites. A
whole-codebase sweep for the slicing idiom
(`grep -rn '\[:\(count\|limit\|n\|top\)' personal_index/`) found **13 further
public "top N / recent N" functions** that leak Python negative-slice
semantics: a negative `limit`/`n`/`top_n` returns `list[:-1]` (all-but-last)
instead of an empty list, while the `0` guard correctly returns `[]`.
Out-of-range (negative) N must yield an empty list, matching the zero guard.

This ticket covers ALL remaining sites of the class in one pass (per the
CLASS SWEEP rule) so the implementer fixes the whole class at once instead of
rediscovering one site per cycle.

## Affected sites (13, all confirmed leaking)
| # | module | function | line | idiom |
|---|--------|----------|------|-------|
| 1 | progress.py | `ProgressStore.list_completed(limit)` | 235 | `completed[:limit]` |
| 2 | content_annotations.py | `AnnotationManager.get_recent(limit)` | 193 | `all_ann[:limit]` |
| 3 | content_collections.py | `CollectionManager.get_recent(limit)` | 326 | `all_c[:limit]` |
| 4 | content_recommender.py | `Recommender.recommend(top_n)` | 185 | `candidates[:top_n]` |
| 5 | content_recommender.py | `Recommender.recommend_for_keywords(top_n)` | 229 | `candidates[:top_n]` |
| 6 | search_suggestions.py | `SearchSuggestions.get_trending(n)` | 151 | `scored[:n]` |
| 7 | search_suggestions.py | `SearchSuggestions.get_related_queries(n)` | 358 | `sorted_related[:n]` |
| 8 | content_monitor/monitor.py | `ContentMonitor.get_disk_usage(top_n)` | 74 | `all_files[:top_n]` |
| 9 | content_linker/linker.py | `ContentLinker.find_related(limit)` | 124 | `results[:limit]` |
| 10 | search_index.py | `SearchIndex.search(limit)` | 148 | `results[:limit]` |
| 11 | content_search.py | `SearchIndex.get_suggestions(limit)` | 483 | `suggestions[:limit]` |
| 12 | content_scoring.py | `ContentScorer.rank(limit)` | 458 | `scored[:limit]` |
| 13 | text_utils.py | `extract_keywords(top_n)` | 152 | `result[:top_n]` |

Note: site 10 is `personal_index/search_index.py` (a distinct module from the
`personal_index/index.py` `SearchIndex.search` already covered by QA-2).

## Exact repro (site 1 - progress, the probed subsystem)
    python3 -c "
    from personal_index.progress import ProgressStore
    s = ProgressStore()
    for i in range(3):
        t = s.create(f'op{i}', total_steps=1); t.start(); t.complete()
    print('limit=0  ->', len(s.list_completed(0)))
    print('limit=-1 ->', len(s.list_completed(-1)))
    print('limit=2  ->', len(s.list_completed(2)))
    "

## Observed output (site 1)
    limit=0  -> 0
    limit=-1 -> 2
    limit=2  -> 2

`list_completed(-1)` returns 2 of 3 (all-but-last) instead of 0.

## Repro + observed for the other sites (all return all-but-last on -1, [] on 0)
    # site 2
    from personal_index.content_annotations import AnnotationManager, Annotation, AnnotationType
    a = AnnotationManager()
    for i in range(3): a.add(Annotation(content_id='u', text=f't{i}', annotation_type=AnnotationType.NOTE))
    len(a.get_recent(-1))   # 2  (expect 0)
    # site 3
    from personal_index.content_collections import CollectionManager
    c = CollectionManager()
    for i in range(3): c.create(name=f'col{i}', description='d')
    len(c.get_recent(-1))   # 2  (expect 0)
    # site 4/5
    from personal_index.content_recommender import Recommender, ContentItem
    r = Recommender()
    for i in range(3): r.add_item(ContentItem(url=f'u{i}', title=f't{i}', keywords=['a','b']))
    seed = ContentItem(url='seed', title='seed', keywords=['a'])
    len(r.recommend(seed, top_n=-1))            # 2  (expect 0)
    len(r.recommend_for_keywords(['a'], top_n=-1))  # 2  (expect 0)
    # site 6
    from personal_index.search_suggestions import SearchSuggestions
    s = SearchSuggestions()
    for q in ['q0','q1','q2']: s.record_search(q)
    len(s.get_trending(-1))   # 2  (expect 0)
    # site 7
    for q in ['python web','python data','javascript web','python web dev']: s.record_search(q)
    len(s.get_related_queries('python web', n=-1))  # 2  (expect 0)
    # site 8
    from personal_index.content_monitor.monitor import ContentMonitor
    # (3 files in a temp dir)
    len(m.get_disk_usage(top_n=-1).largest_files)   # 2  (expect 0)
    # site 9
    from personal_index.content_linker.linker import ContentLinker
    l = ContentLinker()
    for i in range(3): l.add_item(f'i{i}', content='common word here', url=f'http://x.com/{i}', title=f't{i}')
    len(l.find_related('i0', limit=-1))   # 1  (expect 0)
    # site 10
    from personal_index.search_index import SearchIndex
    from personal_index.models import CrawledPage
    si = SearchIndex(index_path='<tmp>/idx.json')
    for i in range(3): si.add(CrawledPage(url=f'u{i}', title=f't{i}', content='common word here'))
    len(si.search('common', limit=-1))   # 2  (expect 0)
    # site 11
    from personal_index.content_search import SearchIndex as CSI
    si = CSI()
    for w in ['apple','apples','appetizer','application']: si.add_item({'id': w, 'title': w, 'content': w})
    len(si.get_suggestions('app', limit=-1))   # 3  (expect 0)
    # site 12
    from personal_index.content_scoring import ContentScorer
    sc = ContentScorer()
    items = [{'keyword_matches': i, 'total_keywords': 1} for i in range(3)]
    len(sc.rank(items, limit=-1))   # 2  (expect 0)
    # site 13
    from personal_index.text_utils import extract_keywords
    len(extract_keywords('a a b b c c d d e e', top_n=-1))   # 4  (expect 0)

## Expected per docs
For every site, the docstring documents a "top N / recent N / up to limit"
contract (e.g. `list_completed`: "List completed trackers, most recent
first"; `get_recent`: "Return up to `limit` annotations"; `get_trending`:
"Get the most trending search queries"; `extract_keywords`: "Extract top N
keywords"). A negative N is out-of-range and must return an empty list,
consistent with the `N=0` -> `[]` guard that every site already implements.
The fix is to clamp the slice bound to `max(0, N)` (or `N if N > 0 else 0`)
before slicing, at each of the 13 sites.

## Deep test
`tests/deep/test_progress_adversarial.py::test_list_completed_negative_limit_returns_empty`
pins site 1 (progress, the probed subsystem) as `xfail-strict` so the suite
stays green while documenting the defect. The other 12 sites are covered by
the repro commands above; the implementer should add a passing regression test
per site when fixing.

## Related
QA-1 (#1028), QA-2 (#1037), QA-3 (#1040) - same defect class, earlier sites.
