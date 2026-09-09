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
- [content-validation.md](content-validation.md) (spec) — `personal_index.content_validation`:
  ValidationError, ValidationResult, ContentValidator.
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
- [content-merger.md](content-merger.md) (spec) — `personal_index.content_merger`:
  MergeSource (6 fields) + MergedContent (8 fields) + ContentMerger (merge, 4 strategies, priority-sorted, empty-guard);
  strategy-never-validated so unrecognized strings silently run concatenate and merge_strategy hides the typo (ARCH-34) contract hole.
- [content-aggregator.md](content-aggregator.md) (spec) — `personal_index.content_aggregator`:
  ContentAggregator (add_source/get_source/merge_all/filter_by_source/get_source_names/clear_source/clear_all/total_items/source_count);
  merge_all dedup key collapses items with both id and title falsy so the default dedup silently drops them (ARCH-35) contract hole.
- [url-dedup.md](url-dedup.md) (spec) — `personal_index.url_dedup`:
  DedupResult + URLDeduplicator (normalize_url/check_duplicate/add_url/deduplicate_urls/get_duplicates/get_stats/get_canonical_url/get_domain_urls/clear, exact + same-domain fuzzy path match);
  get_duplicates/get_stats can never report the duplicates actually detected because only non-duplicates are stored (ARCH-36) contract hole.
- [rate-limiter.md](rate-limiter.md) (spec) — `personal_index.rate_limiter`:
  RateLimitConfig + RateLimitStatus + RateLimiter/TokenBucket (per-domain token bucket: can_request/wait_for_request/get_status/get_wait_time/reset_domain/reset_all/get_all_statuses); can_request consumes a token (not a side-effect-free probe); unvalidated config — window_seconds==0 and max_requests<=0 raise ZeroDivisionError (ARCH-37) contract hole.
- [queue.md](queue.md) (spec) — `personal_index.queue`:
  TaskPriority (int Enum, lower value = higher priority) + TaskStatus (str Enum) + Task (@dataclass(order=True), priority+sequence sort keys) + TaskQueue (heapq min-heap + id dict, enqueue/dequeue/get_task/cancel_task/complete_task/fail_task, size/pending_count/completed_count/get_stats/clear_completed); _evict_lowest pops the heap minimum = the highest-priority task, so overflow drops the most important task while logging "dropping lowest priority" (ARCH-38) contract hole.
- [bookmarks.md](bookmarks.md) (spec) — `personal_index.bookmarks`:
  Bookmark (8-field @dataclass, to_dict/from_dict) + BookmarkManager (add/get/remove/list_all/list_by_category/list_by_tag/list_favorites/toggle_favorite/search/get_categories/get_all_tags/count/save/load); load silently clears and replaces the in-memory set with no merge mode, so unsaved mutations are lost on any load (ARCH-39) contract hole.
- [storage.md](storage.md) (spec) — `personal_index.storage`:
  Storage (data_dir + interests.json/config.json/pages.json; add_interest/get_interests/get_interest/remove_interest/list_interests, save_config/get_config, add_page/get_pages/get_page/remove_page/get_page_count/clear_pages/get_stats); _write_json is non-atomic (direct write, no temp-file-and-rename) and _read_json silently returns the empty default on JSONDecodeError, so an interrupted write destroys the whole store with no signal (ARCH-40) contract hole.
- [tags.md](tags.md) (spec) — `personal_index.tags`:
  Tag (4-field @dataclass, name-keyed eq/hash/lt) + TagStore (store_path + _tags/_page_tags; create_tag/get_tag/list_tags/delete_tag, add_tag_to_page/remove_tag_from_page/get_tags_for_page/get_tags_for_url/get_pages_for_tag/search_by_tag, get_tag_count/get_tagged_page_count/save/remove_page/clear); create_tag silently overwrites color/description AND resets created_at on a name collision while preserving page associations (ARCH-41) contract hole.
- [annotation.md](annotation.md) (spec) — `personal_index.annotation`:
  AnnotationType (str Enum, 7 members) + Annotation (8-field @dataclass, update/to_dict) + AnnotationStore (in-memory, _annotations + _by_url; add/get/get_by_url/get_by_type/update/remove/remove_by_url/search, count property/get_stats); add silently overwrites on an annotation_id collision AND desyncs the _by_url index so get_by_url(old_url) returns the replaced annotation (ARCH-42) contract hole.
- [content-collections.md](content-collections.md) (spec) — `personal_index.content_collections`:
  Collection (7-field @dataclass, add_item/remove_item/contains/item_count/to_dict/from_dict) + CollectionManager (in-memory, _collections + _item_to_collections; create/get/list_all/list_public/list_private/get_items/get_collections_for_item, add_item/add_items/remove_item/clear_items/move_item, update_name/update_description/rename/toggle_public, delete/merge, search/get_recent/count/get_stats, serialize/deserialize); move_item over-promises relocation — it is a single-source remove + add, so an item in multiple collections is not actually moved out of the others (ARCH-43) contract hole.
- [content-pin.md](content-pin.md) (spec) — `personal_index.content_pin`:
  PinnedItem (4-field @dataclass, __post_init__ stamps pinned_at) + ContentPinner (JSON-file-backed, _load/_save; pin/unpin/is_pinned/get_pinned_items/clear) + module-level pin_content/unpin_content/_get_default_pinner; _save is non-atomic (direct write, no temp-file-and-rename) and _load silently clears to {} on JSONDecodeError, so an interrupted write destroys every pin with no signal (ARCH-44) contract hole.
- [content-priority.md](content-priority.md) (spec) — `personal_index.content_priority`:
  PriorityLevel (5-member Enum + from_score) + PriorityConfig (8-field @dataclass, weights+thresholds) + PriorityResult (6-field @dataclass, to_dict) + PriorityCalculator (calculate/batch_calculate/get_summary + private _add_factor/_weighted_total/_recency_score/_interest_score/_engagement_score/_level_for_score); from_score (hardcoded bands, score>0 -> LOW) and _level_for_score (config thresholds, score>=0.2 -> LOW) are two divergent public score->level paths that disagree for score in (0,0.2) and from_score ignores PriorityConfig (ARCH-45) contract hole.
- [content-versioning.md](content-versioning.md) (spec) — `personal_index.content_versioning`:
  ContentVersion (5-field @dataclass, __post_init__ stamps created_at) + ContentVersioning (JSON-file-backed, _load/_save; create_version/get_versions/get_version/delete_version/rollback_to/clear_versions) + module-level create_version/get_versions on a lazy default instance; _save is non-atomic (direct write, no temp-file-and-rename) and _load silently clears to {} on JSONDecodeError, so an interrupted write destroys every version for every item with no signal (ARCH-46) contract hole.
- [content-rollback.md](content-rollback.md) (spec) — `personal_index.content_rollback`:
  RollbackPoint (5-field @dataclass) + ContentRollback (in-memory, _rollback_points; create_rollback_point/get_rollback_points/rollback/clear); in-memory-only — no save/load, so every rollback point is lost on process exit (ARCH-47) contract hole.
- [content-exporter.md](content-exporter.md) (spec) — `personal_index.content_exporter`:
  ContentExporter (export/export_to_file/detect_format, SUPPORTED_FORMATS html/json/markdown/rss); per-format escaping is inconsistent — HTML uses html.escape, RSS uses xml_escape, and Markdown escapes nothing, so a Markdown title/link/description with Markdown-significant chars silently produces broken output (ARCH-48) contract hole.
- [content-digest.md](content-digest.md) (spec) — `personal_index.content_digest`:
  DigestEntry (to_dict) + DigestSection (count property) + ContentDigest (to_dict/format_markdown/format_text) + DigestGenerator (add_entry/add_entries/generate/clear, score-desc sort, tags|source|none grouping, per-section cap); the summary item count double-counts multi-tag entries and is decoupled from total_entries (ARCH-49) contract hole.
- [content-notifications.md](content-notifications.md) (spec) — `personal_index.content_notifications`:
  NotificationType/NotificationChannel (Enums) + NotificationRule (matches, AND-conditions, cooldown) + Notification (to_dict) + NotificationManager (add_rule/remove_rule/evaluate_event/get_undelivered/mark_delivered/mark_all_delivered/get_recent/clear_old); channels are recorded but never dispatched and `delivered` is a caller-toggled flag with no actual send (ARCH-50) contract hole.
- [content-batch.md](content-batch.md) (spec) — `personal_index.content_batch`:
  BatchResult (success_rate/to_dict) + BatchProcessor (process/process_with_retry/process_item_by_item, batch_size chunking, on_progress, _batch_counter); only ValueError is caught per batch/item so any other processor exception aborts the whole run (ARCH-52) contract hole.
- [content-search.md](content-search.md) (spec) — `personal_index.content_search`:
  Snippet (to_dict) + SnippetExtractor (extract/highlight_text, guard/no-match/match paths, max_snippets cap) + SearchIndex (add_item/add_items/remove_item, search with tf/tfidf/bm25 ranking + filters + highlight, item_count/term_count, get_suggestions, save_index/load_index, highlight_matches) + ContentSearch facade; add_item does not remove the old tokens on a re-add, so stale tokens survive an in-place re-index (ARCH-53) contract hole.
- [content-feed.md](content-feed.md) (spec) — `personal_index.content_feed`:
  FeedFormat (RSS/ATOM) + FeedItem (to_dict/from_dict, id/published/updated defaults) + FeedGenerator (add_item/add_items/clear/get_feed_type/generate, RSS 2.0 + Atom 1.0, to_dict/from_dict); to_dict/from_dict is a lossy round-trip — it drops max_items and feed_id, so the item cap and Atom id silently reset (ARCH-54) contract hole.

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
