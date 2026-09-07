# Personal Index - Documentation

A personal web search engine that crawls, filters, scores, tags, and indexes
web content based on your interests.

## Index

Each subsystem page is marked **(spec | stub | stale)**:
- **spec** — the page matches CURRENT code; every divergence found while
  writing it is listed in its "contract holes" section and ticketed.
- **stub** — placeholder; not yet audited against code.
- **stale** — known to diverge from current code; needs re-audit.

### Contract standard
- [CONTRACTS.md](CONTRACTS.md) (spec) — the exact-contract docstring standard
  (guard paths, return-object fields, side effects) + pinning-test method.

### Core subsystems
- [content-model.md](content-model.md) (spec) — `personal_index.models`:
  Interest, CrawledPage, IndexedPage, SearchResult, Page, PipelineStats.
- [search-index.md](search-index.md) (spec) — `personal_index.index`:
  SearchIndex (add/remove/get/list/clear/search) + word index + JSON persistence.
- [dedup.md](dedup.md) (spec) — `personal_index.content_dedup`:
  ContentDeduplicator (hash / url / similarity / all) + DedupResult.
- [scoring.md](scoring.md) (spec) — `personal_index.content_scoring`:
  ContentScorer, ScoreWeights, ContentScore, the six factors.
- [cache.md](cache.md) (spec) — `personal_index.cache`:
  LRUCache, TTLCache, CacheDecorator.
- [timeline.md](timeline.md) (spec) — `personal_index.content_timeline`:
  Timeline, TimelineEvent, TimelineEventType.
- [validation.md](validation.md) (spec) — `personal_index.content_validator`:
  ValidationRule, RuleResult, the built-in rules.
- [analytics.md](analytics.md) (spec) — `personal_index.analytics`:
  AnalyticsTracker (record/compute/get stats/save/load) + SearchEvent, CrawlEvent, AnalyticsData.
- [content-categorizer.md](content-categorizer.md) (spec) — `personal_index.content_categorizer`:
  ContentCategorizer (add/remove/get topics, categorize, categorize_batch) + TopicCategory, TopicScore, CategorizationResult.

### Legacy pages (pre-split; not yet re-audited)
- [ARCHITECTURE.md](ARCHITECTURE.md) (stale) — 6-stage pipeline overview;
  module list predates the package reorg (many `cli_*.py` files listed do not
  exist; see contract holes in the core pages).
- [API_REFERENCE.md](API_REFERENCE.md) (stale) — PipelineRunner / SearchIndex /
  InterestStore / TagStore / ContentFilter / ContentScorer signatures; some
  signatures drift from current code.
- [MODULES.md](MODULES.md) (stale) — core module list; predates the package reorg.
- [USER_GUIDE.md](USER_GUIDE.md) (stub) — CLI workflows.
- [QUICKSTART.md](QUICKSTART.md) (stub) — 5-minute setup.
- [CHANGELOG.md](CHANGELOG.md) (stub) — release notes.
