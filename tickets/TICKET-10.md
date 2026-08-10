# TICKET-10: Duplicate modules with overlapping functionality

## Title
Four pairs of modules have overlapping names and functionality

## Evidence
The following module pairs exist side-by-side with overlapping purposes:

### 1. `dedup.py` vs `content_dedup.py`
- `personal_index/dedup.py` (100 lines) — hash-based dedup with `DeduplicationEngine`, `DocumentHash`
- `personal_index/content_dedup.py` (490 lines) — more sophisticated dedup with `SimilarityMethod` enum, Jaccard, cosine similarity
- Neither is imported by production code
- Both have tests: `test_dedup.py` and `test_content_dedup.py`

### 2. `health.py` vs `content_health.py`
- `personal_index/health.py` — general health checks
- `personal_index/content_health.py` — content-specific health monitoring
- Both have tests

### 3. `scheduler.py` vs `content_scheduler.py`
- `personal_index/scheduler.py` — imported by `formatter.py` and `cli.py`
- `personal_index/content_scheduler.py` — NOT imported by any production code
- `content_scheduler.py` appears to be a newer/more specific version

### 4. `summarizer.py` vs `content_summarizer.py`
- `personal_index/summarizer.py` — NOT imported by any production code
- `personal_index/content_summarizer.py` — NOT imported by any production code
- Both are dead code

## Impact
- Confusion about which module to use
- Duplicated logic that may diverge over time
- `content_scheduler.py` and both summarizers are dead code
- `content_dedup.py` has more features but `dedup.py` is the one tested

## Suggestion
1. **dedup/content_dedup**: Consolidate into `content_dedup.py` (more features), remove `dedup.py`, update tests
2. **health/content_health**: Clarify the distinction or merge. `health.py` should be system-level, `content_health.py` for content URLs
3. **scheduler/content_scheduler**: Remove `content_scheduler.py` (dead code) or integrate it into `scheduler.py`
4. **summarizer/content_summarizer**: Pick one implementation and remove the other. Both are currently dead code.
