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
- [content-filter.md](content-filter.md) (spec) — `personal_index.content_filter`:
  FilterConfig, ContentFilter (should_include / get_filter_reasons / filter_pages),
  eight ordered checks, silent pattern-compile guard, interest-match side effects.
- [pipeline-orchestrator.md](pipeline-orchestrator.md) (spec) — `personal_index.pipeline_orchestrator`:
  PipelineOrchestrator (run / run_from_files / search / close) + PipelineResult; crawl→filter→score→tag→index.
- [cli.md](cli.md) (spec) — `personal_index.cli`:
  the click command surface (main group + interests/tags/schedule/config subgroups + top-level commands),
  shared store getters, data-dir/config bootstrap, guard paths.
- [search-facets.md](search-facets.md) (spec) — `personal_index.search_facets`:
  Facet/FacetValue/FacetType models, FacetBuilder (build/aggregate), FacetedSearch (search/filters/facets) + SearchResults.
- [content-summarizer.md](content-summarizer.md) (spec) — `personal_index.content_summarizer`:
  SummaryResult, summarize (guard/short-text/scoring paths), summarize_page (title-prepended, empty-content guard).
- [content-recommender.md](content-recommender.md) (spec) — `personal_index.content_recommender`:
  Recommendation, ContentItem, Recommender (add_item/add_items/recommend/recommend_for_keywords/clear/item_count), _extract_keywords, Jaccard sub-scores, negative-top_n + case-sensitivity contract holes.
- [content-tagger.md](content-tagger.md) (spec) — `personal_index.content_tagger`:
  Tag, TopicDetector (detect/add_topic/remove_topic/get_all_topics, 20 built-in topics, substring keyword matching),
  TagResult, ContentTagger (tag/batch_tag/get_tag_statistics/add_topic/clear_statistics), dead-weight + substring-match contract holes.
- [content-scraper.md](content-scraper.md) (spec) — `personal_index.scraper`:
  ScraperConfig, ScrapedContent, HTMLScraper (scrape + 8 private extractors),
  charset override order, dead remove_scripts flag + word_count/truncation contract holes.
- [content-rss.md](content-rss.md) (spec) — `personal_index.rss`:
  FeedEntry, Feed (entry_count / get_recent_entries), RSSParser (parse + is_feed, RSS 2.0 + Atom),
  silent empty-feed for non-feed root tags + RSS-never-updates contract holes.
- [content-sitemap.md](content-sitemap.md) (spec) — `personal_index.sitemap` + `personal_index.sitemap_builder`:
  SitemapEntry, Sitemap (url_count / sitemap_count / get_urls), SitemapParser (parse / parse_text_sitemap /
  filter_by_priority / filter_by_changefreq / get_recent_entries), SitemapBuilder (add_entry / build /
  build_sitemap_index / split_into_chunks), dead MAX_SITEMAP_SIZE_BYTES + dual-SitemapEntry contract holes.
- [content-robots.md](content-robots.md) (spec) — `personal_index.crawler.robots`:
  RobotsRule, RobotsPolicy (can_fetch / _matches, longest-pattern-wins, default-allow),
  parse_robots_txt / is_allowed / RobotsParser; dead duplicate robots_parser module +
  RobotsParser.parse-never-populates-_policies + empty-Disallow contract holes.
- [content-importer.md](content-importer.md) (spec) — `personal_index.content_importer`:
  ContentImporter (import_content / batch_import, 5 formats json|html|markdown|rss|csv),
  per-format item shapes; inconsistent cross-format shape + untyped batch_import +
  stdlib-ET rss + JSON-scalar-TypeError contract holes.
- [importer.md](importer.md) (spec) — `personal_index.importer`:
  ImportResult + Importer (import_from_file / import_from_content / import_opml,
  formats json|csv|html|xml|necko|netscape); inconsistent total_skipped across formats +
  OPML-unreachable-via-dispatch + dead path param + stray trailing docstring contract holes.
- [content-extractor.md](content-extractor.md) (spec) — `personal_index.content_extractor`:
  ExtractedContent + ContentExtractor (extract / extract_readability_score, og:title-preferred title,
  meta/canonical/language/author, headings/links/images, whitespace-normalized truncated text);
  word_count-vs-text readability divergence + pre-truncation word_count + title.string contract holes.
- [content-reader.md](content-reader.md) (spec) — `personal_index.content_reader`:
  ReadResult + PageView + ContentReader (add/add_many/get/list_all/paginate, filter_by_tags/score,
  search_titles/content, format_item/page, clear/count); duplicate-URL get-vs-list divergence +
  empty-reader inverted range + empty-tags-returns-all contract holes.
- [content-scheduler.md](content-scheduler.md) (spec) — `personal_index.content_scheduler`:
  TaskStatus + ScheduledTask (cron parse / next_run / is_due / run / to_dict) + TaskScheduler
  (add_task/get_task/list_tasks/remove_task/enable_task/disable_task/run_due_tasks/get_stats);
  passive-scheduler-no-loop + stale-next_run + no-add_task-validation contract holes.
- [content-webhooks.md](content-webhooks.md) (spec) — `personal_index.content_webhooks`:
  WebhookEventType + WebhookEndpoint (should_retry) + WebhookPayload + WebhookManager
  (register_endpoint/remove_endpoint/dispatch_event/mark_delivered/mark_failed/get_stats/get_payload_json);
  signature-not-verifiable + exhausted-lands-in-delivered + no-http-delivery contract holes.
- [search-suggestions.md](search-suggestions.md) (spec) — `personal_index.search_suggestions`:
  Suggestion (to_dict 4dp) + TrendingEntry (age_seconds/record) + SearchSuggestions
  (add_search_history/add_tags/add_keywords/record_search/get_trending/suggest/get_related_queries/clear/to_dict/from_dict);
  trending-exact-match-score-exceeds-1.0 contract hole.
- [url-classifier.md](url-classifier.md) (spec) — `personal_index.url_classifier`:
  URLCategory (9 members, ERROR/UNKNOWN dead), ClassificationResult (metadata never populated),
  URLClassifier (classify/classify_batch/get_category_counts, 6-rule fixed-order first-match),
  /static/+/assets/ overlap (MEDIA dead) + duplicate /redirect pattern contract holes.
- [robots-cache.md](robots-cache.md) (spec) — `personal_index.robots_cache`:
  RobotsCacheEntry (is_expired/allows_agent) + RobotsCache (get/put/invalidate/invalidate_all/size/domains/get_stats);
  "Thread-safe" claim with no locking (ARCH-32) + allows_agent-ignores-values + FIFO-not-LRU contract holes.
- [content-enricher.md](content-enricher.md) (spec) — `personal_index.content_enricher`:
  EnrichedContent (12 fields, to_dict) + ContentEnricher (enrich/batch_enrich, sentiment/complexity, html-detected flags);
  batch_enrich-cannot-pass-html so has_code/has_links/has_images always-False (ARCH-33) + language-never-computed contract holes.

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
