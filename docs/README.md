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
- [search_index.md](search_index.md) (spec) — `personal_index.search_index`:
  SearchIndex (add/remove/get/count/urls/clear/search) + word index + JSON persistence; distinct from `personal_index.index` (search-index.md) — `index_path`/`CrawledPage`/`(url,float)` tuples, no close/context-manager; `_save` non-atomic + unflushed so a crash mid-write truncates the file and the next `_load` silently degrades to empty (ARCH-71) contract hole.
- [dedup.md](dedup.md) (spec) — `personal_index.content_dedup`:
  ContentDeduplicator (hash / url / similarity / all) + DedupResult.
- [encoding.md](encoding.md) (spec) — `personal_index.encoding`:
  EncodingDetector (detect cascade / decode / encode / convert) + EncodingResult + whitespace/control-char helpers; `decode` silently degrades to lossy UTF-8 (`errors="replace"`) on a bad/unknown explicit encoding instead of raising (ARCH-77) contract hole.
- [scoring.md](scoring.md) (spec) — `personal_index.content_scoring`:
  ContentScorer, ScoreWeights, ContentScore, the six factors.
- [cache.md](cache.md) (spec) — `personal_index.cache`:
  LRUCache, TTLCache, CacheDecorator.
- [timeline.md](timeline.md) (spec) — `personal_index.content_timeline`:
  Timeline, TimelineEvent, TimelineEventType.
- [pagination.md](pagination.md) (spec) — `personal_index.pagination`:
  PageParams (clamped page/per_page, offset/limit) + PageResult (total_pages/has_next/has_prev/next_page/prev_page/start_index/end_index/to_dict, one-way) + Paginator (get_page/total_items/total_pages/iterate_pages); Paginator.total_pages divides by the raw unclamped constructor per_page so per_page=0 raises ZeroDivisionError while get_page/iterate_pages silently clamp to 1 (ARCH-58) contract hole.
- [validation.md](validation.md) (spec) — `personal_index.content_validator`:
  ValidationRule, RuleResult, the built-in rules.
- [analytics.md](analytics.md) (spec) — `personal_index.analytics`:
  AnalyticsTracker (record/compute/get stats/save/load) + SearchEvent, CrawlEvent, AnalyticsData.
- [stats.md](stats.md) (spec) — `personal_index.stats`:
  StatsCollector (get_index_stats) + IndexStats, CrawlStats; read-only index aggregate over a SearchIndex, no persistence; distinct from analytics (event log) and content_analytics (content items); interest stats are derived from CrawledPage.matched_interests, not an InterestStore — the public interest_store field is never read and CrawlStats is never produced (ARCH-86) contract hole.
- [metrics.md](metrics.md) (spec) — `personal_index.metrics`:
  SystemMetrics (11-field @dataclass, to_dict) + MetricsCollector (increment_counter/set_gauge/record_histogram/collect_system_metrics/get_histogram_stats/get_report/reset); distinct from stats (index aggregate) and analytics (event log); collect_system_metrics populates uptime/memory_used/disk_* but cpu_percent and memory_total_mb are never collected and stay at their 0.0 defaults — memory_total_mb is serialized by to_dict yet never populated and the docstring is silent about it (ARCH-88) contract hole.
- [performance-monitor.md](performance-monitor.md) (spec) — `personal_index.performance_monitor`:
  MetricSample + MetricStats (mean/stddev/p50/p95/p99 approximations) + PerformanceMonitor (record/timer/get_stats/get_all_stats/reset/get_recent_samples) + TimerContext; distinct from metrics (SystemMetrics/MetricsCollector) and stats (index aggregate); window_size bounds the _samples ring but NOT the _stats aggregate — get_stats() is a silent lifetime count/mean/min/max over all recorded values, not the retained window (ARCH-89) contract hole.
- [content-categorizer.md](content-categorizer.md) (spec) — `personal_index.content_categorizer`:
  ContentCategorizer (add/remove/get topics, categorize, categorize_batch) + TopicCategory, TopicScore, CategorizationResult.
- [content-filter.md](content-filter.md) (spec) — `personal_index.content_filter`:
  FilterConfig, ContentFilter (should_include / get_filter_reasons / filter_pages),
  eight ordered checks, silent pattern-compile guard, interest-match side effects.
- [interests.md](interests.md) (spec) — `personal_index.interests`:
  InterestStore (add/remove/get/list_all/get_enabled/toggle, get_all_keywords/get_all_url_patterns/get_all_topics, update_priority/matches_any/clear/total_score, JSON persistence); distinct from content_scoring/content_filter/content_tagger/content_priority (which consume it); _load degrades to empty for corrupt/non-dict/null/non-dict-value/missing-name but a valid-JSON-dict record with an out-of-enum interest_type or match_mode raises ValueError (not in the except tuple) so the constructor crashes instead of degrading (ARCH-85) contract hole.
- [pipeline-orchestrator.md](pipeline-orchestrator.md) (spec) — `personal_index.pipeline_orchestrator`:
  PipelineOrchestrator (run / run_from_files / search / close) + PipelineResult; crawl→filter→score→tag→index.
- [pipeline-runner.md](pipeline-runner.md) (spec) — `personal_index.pipeline_runner`:
  PipelineRunner (run / run_from_files / add_page_directly / close) + PipelineStats; crawl→extract→filter→score→tag→index; distinct from pipeline_orchestrator (PipelineOrchestrator/PipelineResult); `stages` is documented as an arbitrary subset but only a prefix of the fixed stage order produces meaningful results — a non-prefix subset (e.g. {"index"}) silently no-ops (ARCH-91) contract hole.
- [cli.md](cli.md) (spec) — `personal_index.cli`:
  the click command surface (main group + interests/tags/schedule/config subgroups + top-level commands),
  shared store getters, data-dir/config bootstrap, guard paths.
- [cli_verify.md](cli_verify.md) (spec) — `personal_index.cli_verify`:
  the `verify` click command + `_check_*`/`_run_*`/`_verify_*` self-test helpers (data-dir/interest/tag/search-index/filter/scorer checks + full-pipeline self-test); distinct from `personal_index.cli` (cli.md, the main group + subgroups) and the pipeline modules (which run the pipeline; this only checks it); `_run_filter` (line 209, `tuple[bool, str]`) is dead code — the full pipeline calls the `bool`-returning `_verify_filter` (line 291) instead (ARCH-97) contract hole.
- [cli_dedup.md](cli_dedup.md) (spec) — `personal_index.cli_dedup`:
  the `dedup` click command + `_load_indexed_content`/`_build_dedup_items`/`_dispatch_dedup`/`_display_result`/`_display_duplicate_groups`/`_remove_duplicates` helpers (hash/url/similarity/all dedup over indexed pages, dry-run guard); distinct from `personal_index.cli` (cli.md, the main group) and the underlying engine `personal_index.content_dedup` (dedup.md); the `Score:` line (line 118) prints `DuplicateGroup.similarity_score`, which for similarity groups is the configured `similarity_threshold` (content_dedup.py:388), not the measured Jaccard overlap (ARCH-102) contract hole.
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
- [keyword-extractor.md](keyword-extractor.md) (spec) — `personal_index.keyword_extractor`:
  Keyword (text/frequency/score/positions, __post_init__ normalizes None->[]) + KeywordExtractor
  (extract/extract_phrases/extract_top_n/compute_term_frequency/compare_keywords, score=freq*log(1+freq)) +
  module fn extract_keywords; extract_top_n n-silently-capped-by-constructor-max_keywords (ARCH-57) contract hole.
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
  thread-safe via threading.Lock (ARCH-32 resolved cycle 219) + max_entries<=0 no-op put guard + allows_agent-ignores-values + FIFO-not-LRU contract holes.
- [domains.md](domains.md) (spec) — `personal_index.domains`:
  DomainRule (to_dict/from_dict, non-mapping degrades to empty-domain rule, unknown keys ignored) + DomainManager (add_allow/add_block/is_allowed/is_blocked/record_page/get_page_count/reset_counts/remove/list_rules/get_max_depth, JSON persistence, in-memory page counts); exact-match case-sensitive keys, whitelist = any allow rule, but remove() does not recompute _has_whitelist so removing the last allow rule silently flips unlisted domains to deny-all (ARCH-84) contract hole.
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
- [url-utils.md](url-utils.md) (spec) — `personal_index.url_utils`:
  22 public helpers (is_valid_url/normalize_url/is_canonical/extract_domain (+get_domain alias)/get_path/get_query_string/get_fragment/extract_subdomain/get_tld/get_url_depth/is_same_domain/is_internal_link/urls_are_equivalent/is_robotstxt/is_sitemap/is_excluded_url/remove_query_params/strip_tracking_params/url_to_path/join_urls/resolve_relative_url/extract_all_urls); get_tld returns only the LAST dot-label so two-label TLDs (co.uk→uk, com.au→au) and dotless hosts (intranet→intranet) are silently wrong (ARCH-61) contract hole.
- [url-filter.md](url-filter.md) (spec) — `personal_index.url_filter`:
  UrlFilterRule (pattern/is_blacklist/description, matches: exact -> fnmatch -> re: regex via re.search, re.error swallowed to False) + UrlFilter (add_blacklist/add_whitelist, is_allowed/is_blocked/filter_urls/get_blocked_urls/get_matching_rule, blacklist_count/whitelist_count, clear/clear_blacklist/clear_whitelist); whitelist takes precedence over blacklist; is_blacklist is a public field the decision logic never reads — block/allow is decided purely by list membership, so the field is redundant with membership and its True default is unreachable via the public API (ARCH-87) contract hole.
- [rate-limiter.md](rate-limiter.md) (spec) — `personal_index.rate_limiter`:
  RateLimitConfig + RateLimitStatus + RateLimiter/TokenBucket (per-domain token bucket: can_request/wait_for_request/get_status/get_wait_time/reset_domain/reset_all/get_all_statuses); can_request consumes a token (not a side-effect-free probe); unvalidated config — window_seconds==0 and max_requests<=0 raise ZeroDivisionError (ARCH-37) contract hole.
- [throttle.md](throttle.md) (spec) — `personal_index.throttle`:
  ThrottleRule (rate_per_second) + ThrottleState + ThrottleManager (set_rule/get_rule/should_throttle/wait_if_needed/get_stats/reset); should_throttle is a side-effect-free probe, wait_if_needed sleeps and records; rate_per_second divides by raw window_seconds so window_seconds==0 raises ZeroDivisionError on the 2nd+ request (probe safe, wait path crashes) (ARCH-59) contract hole.
- [queue.md](queue.md) (spec) — `personal_index.queue`:
  TaskPriority (int Enum, lower value = higher priority) + TaskStatus (str Enum) + Task (@dataclass(order=True), priority+sequence sort keys) + TaskQueue (heapq min-heap + id dict, enqueue/dequeue/get_task/cancel_task/complete_task/fail_task, size/pending_count/completed_count/get_stats/clear_completed); _evict_lowest pops the heap minimum = the highest-priority task, so overflow drops the most important task while logging "dropping lowest priority" (ARCH-38) contract hole.
- [bookmarks.md](bookmarks.md) (spec) — `personal_index.bookmarks`:
  Bookmark (8-field @dataclass, to_dict/from_dict) + BookmarkManager (add/get/remove/list_all/list_by_category/list_by_tag/list_favorites/toggle_favorite/search/get_categories/get_all_tags/count/save/load); load silently clears and replaces the in-memory set with no merge mode, so unsaved mutations are lost on any load (ARCH-39) contract hole.
- [bookmark_export.md](bookmark_export.md) (spec) — `personal_index.bookmark_export`:
  BookmarkExportResult (5-field @dataclass, __post_init__ stamps exported_at) + BookmarkExporter (export_json/export_html/export_opml, export dispatch, export_to_file, SUPPORTED_FORMATS json/html/opml, _EXTENSION_MAP json/html/htm/opml); export_to_file with an unknown extension and no explicit fmt leaves fmt=None and reports the literal "Unsupported format: None" instead of naming the inspected extension (ARCH-79) contract hole.
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
- [content-export-csv.md](content-export-csv.md) (spec) — `personal_index.content_export_csv`:
  ExportFormat (4-member str-Enum) + ExportStats (4-field @dataclass, dead type — never returned) + CSVExporter (stateless; export/export_to_file/get_stats, _get_columns defaults-first-then-alphabetical, _format_value None->""/datetime->isoformat/bool->str/list-tuple->"; "-joined/dict->json); export degrades unrecognized format to CSV and clamps negative limit to 0, but export_to_file hardcodes encoding="utf-8" on open() and forwards the caller encoding into export() where it is never read, so a non-utf-8 encoding request is silently dropped (ARCH-80) contract hole.
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
- [content-health.md](content-health.md) (spec) — `personal_index.content_health`:
  HealthStatus/IssueSeverity/HealthIssue/HealthCheckResult/HealthReport/ContentHealthCheck + ContentHealthChecker (check_item 7-check pipeline, check_all aggregate report); to_dict exists on HealthIssue/HealthCheckResult but there is no from_dict and HealthReport has no to_dict, so a serialized report cannot be reloaded (ARCH-55) contract hole.
- [export.md](export.md) (spec) — `personal_index.export`:
  ExportResult (5-field @dataclass, __post_init__ stamps exported_at) + Exporter (export_to_file/export_to_content/export_filtered, manager accessor, SUPPORTED_FORMATS json/csv/html/xml/markdown/opml, EXTENSION_MAP); export_to_file/export_to_content/export_filtered degrade an unsupported format to ExportResult(errors=[...])/None without raising, but _export_html opens one <DL><p> and closes with two </DL> tags, so the Netscape HTML is structurally malformed (ARCH-81) contract hole.
- [export_markdown.md](export_markdown.md) (spec) — `personal_index.export_markdown`:
  ExportFormat (3-member str-Enum markdown/html/plain_text) + ExportConfig (5-field @dataclass, __post_init__ validates sort_by/group_by) + MarkdownExporter (export dispatch, _sort_items/_group_items/_render_md_item/_truncate) + module-level export_to_md/save_markdown/export_markdown; export never raises on a well-formed list and returns "" on empty input, but include_summary is inverted — the default (False) keeps the FULL content and True replaces it with a lossy 200-char truncation (ARCH-82) contract hole.
- [formatter.md](formatter.md) (spec) — `personal_index.formatter`:
  11 module-level pure str-returning display helpers (format_search_results, format_interest, format_crawl_stats, format_index_page, format_schedule_job, format_table, format_duration, format_file_size, format_timestamp, truncate, highlight) — no classes, no state, no I/O; none raise on documented inputs (missing dict keys default, falsy/empty inputs hit a guard, unparseable timestamps degrade to the raw string), but format_table is asymmetric on ragged rows — a row LONGER than the header silently drops the excess cells (lossy) while a row SHORTER is padded with empty cells (ARCH-83) contract hole.
- [link-analyzer.md](link-analyzer.md) (spec) — `personal_index.link_analyzer`:
  LinkStats/LinkAnalysisResult + LinkAnalyzer (analyze/analyze_batch/get_aggregate_stats, _is_internal/_is_suspicious); get_aggregate_stats unions the top-20-truncated domain_distribution, so unique_external_domains undercounts once a page has >20 distinct external domains (ARCH-56) contract hole.
- [link_preview.md](link_preview.md) (spec) — `personal_index.link_preview`:
  LinkPreview (8 str fields, all default "") + LinkPreviewGenerator (generate, _fallback_chain/_og_or_twitter/_extract_og_tag/_extract_twitter_tag/_extract_meta/_extract_title_tag/_resolve_image_url, in-memory, no persistence); `url` is read only from `og:url` with no fallback to `base_url`, so `base_url` is honored for `image_url` (urljoin) but silently dropped for the canonical `url` field when `og:url` is absent (ARCH-78) contract hole.
- [text-utils.md](text-utils.md) (spec) — `personal_index.text_utils`:
  15 pure helpers (normalize_whitespace, remove_html_tags, truncate_text, extract_sentences, extract_paragraphs, word_frequency, extract_keywords, levenshtein_distance, similarity_ratio, slugify, highlight_text, count_words, count_characters, read_time_minutes, tokenize); read_time_minutes divides by raw wpm with no guard, so wpm==0 raises ZeroDivisionError and wpm<0 silently returns 1 (ARCH-60) contract hole.
- [content-type.md](content-type.md) (spec) — `personal_index.content_type`:
  ContentTypeInfo (is_downloadable) + ContentTypeDetector (detect_from_url/filename/extension/bytes, classify, should_index); `.svg` dual-membership (TEXT checked before MEDIA) so `.svg` is always `text`/indexable + `is_media` computed with two divergent category sets (ARCH-66) contract holes.
- [content-annotations.md](content-annotations.md) (spec) — `personal_index.content_annotations`:
  AnnotationType (5-member str Enum) + Annotation (update_text/add_tag/remove_tag/to_dict/from_dict) + AnnotationManager (add/get/get_by_*/get_all/get_recent/update_text/add_tag/remove_tag/delete/delete_by_content_id/search/count/get_stats/clear/serialize/deserialize); `add()` is not idempotent — re-adding an `annotation_id` overwrites the primary store but appends a duplicate to each secondary index, so `get_by_*` return the same annotation twice (ARCH-67) contract hole.
- [content-api.md](content-api.md) (spec) — `personal_index.content_api`:
  ContentAPI (handle_request + _match_route chain: health/stats/content CRUD/search/export) + RequestLogger middleware; `_validate_content` is dead in the production request path — it is only called from tests, so a POST/PUT with a >200-char title or non-list tags returns 201/200 instead of 400 (ARCH-68) contract hole.
- [content-changelog.md](content-changelog.md) (spec) — `personal_index.content_changelog`:
  ChangeEntry (plain @dataclass, no runtime type check) + ContentChangelog (add_entry/get_entries/clear, in-memory, no persistence/serialization); get_entries returns a SHALLOW copy — a new list but the ChangeEntry objects and their details dicts are shared references, so mutating a returned entry corrupts the stored entry (ARCH-69) contract hole.
- [content-analytics.md](content-analytics.md) (spec) — `personal_index.content_analytics`:
  ContentAnalytics (add_items/total_items, get_tag_counts/get_tag_distribution/get_unique_tags_count, get_title/description_lengths + avg, get_items_with_links/get_link_ratio, get_items_by_tag, clear, in-memory, no persistence/serialization); get_items_by_tag substring-matches a string `tags` value while get_tag_counts ignores it, so the two tag methods disagree on the same item (ARCH-70) contract hole.
- [backup.md](backup.md) (spec) — `personal_index.backup`:
  BackupManifest (@dataclass, to_dict/from_dict) + BackupManager (create_backup/list_backups/restore_backup/delete_backup/get_backup_info/get_total_backup_size/cleanup_old_backups, tar/tar.gz + JSON manifest); distinct from `personal_index.content_backup.backup_manager` (a different BackupManager); restore_backup silently overwrites pre-existing files in target_dir with no guard (ARCH-72) contract hole.
- [fuzzy_search.md](fuzzy_search.md) (spec) — `personal_index.fuzzy_search`:
  FuzzyMatch (dataclass) + levenshtein_distance/levenshtein_similarity (module fns) + FuzzySearcher (search/search_in_dict/_compute_score/_char_match_score/_find_match_indices/highlight/highlight_html/search_with_highlight); highlight_html inserts the searched text raw with no HTML entity escaping, so `<`/`>`/`&` in a title pass through into the returned markup (ARCH-73) contract hole.
- [serializer.md](serializer.md) (spec) — `personal_index.serializer`:
  SerializationError/DeserializationError + SerializationConfig (indent/ensure_ascii/default_handler/include_none) + Serializer (to_json/from_json/to_csv/from_csv/to_dict + _dataclass_to_dict/_prepare/_prepare_row/_default_handler); to_csv(include_header=False) emits a headerless CSV but from_csv always treats the first line as the header, so the round-trip silently corrupts the data (ARCH-74) contract hole.
- [tfidf.md](tfidf.md) (spec) — `personal_index.tfidf`:
  TfidfScorer (add_document/remove_document/compute_tfidf/score_query/rank_documents/document_count/vocabulary_size/get_top_terms/clear, in-memory, no persistence); add_document increments the corpus count even for a zero-term (empty/all-stopword) document, which inflates the IDF denominator and shifts every existing document's TF-IDF score (ARCH-75) contract hole.
- [url_history.md](url_history.md) (spec) — `personal_index.url_history`:
  URLVisit (dataclass: url/timestamp/status_code/content_length/title/user_agent/response_time_ms/error; __post_init__ auto-fills timestamp; to_dict 8 keys; from_dict via cls(**data)) + URLHistory (record/get_visits/get_unique_urls/get_stats/get_domain_stats/clear/save/load/_trim, in-memory + JSON persistence); load() degrades gracefully for missing/invalid-JSON/non-list but a valid-JSON list with a malformed record (unexpected key or missing url) raises TypeError because the from_dict comprehension is outside the try/except (ARCH-76) contract hole.
- [cycle-signals.md](cycle-signals.md) (spec) — `personal_index.cycle_signals`:
  codemap signal extractor (build_tree/format_tree/load_codemap, signal_no_tests/oversized/dead_code/duplicates/errors/coverage S1-S6, extract/format_for_auditor/main CLI); build_tree drops a package's own module when the node also has children — the node's stats.modules still counts it but no modules key is emitted, so a package with both an __init__.py and submodules is counted yet invisible in the tree (ARCH-90) contract hole.

- [session.md](session.md) (spec) — `personal_index.session`:
  crawl-session tracker (SessionStatus enum, SessionStats dataclass, CrawlSession lifecycle, SessionManager registry + JSON persistence); SessionStats.to_dict serializes domains_seen and errors as COUNTS (len/set, error_count) and load_session restores only the 5 numeric fields, so a save/load round-trip silently drops the error messages and the domain set — counts survive, contents do not (ARCH-92) contract hole.
- [publish_dashboard.md](publish_dashboard.md) (spec) — `personal_index.publish_dashboard`:
  publisher CLI (run/regenerate/validate_sync/_copy_dashboard_files/_git_commit_push/publish/main) that ships the generated dashboard + codemap to belarusian/search; validate_sync's 'in sync' docstring over-promises bidirectional equality but the comparison loop is one-sided (JSON→HTML only), so an HTML-embedded summary with extra keys still returns sync True (ARCH-93) contract hole.

- [docs_generator.md](docs_generator.md) (spec) — `personal_index.docs_generator`:
  dashboard/codemap generator (scan_modules/_parse_module/run_ruff/run_mypy/run_pytest/detect_dependencies/fetch_recent_commits/_compute_signals/_render_test_bars/generate_dashboard/generate_metadata_json/generate/generate_fast); the full pipeline `generate` never calls `_attribute_test_counts` (only `generate_fast` does), so per-source-module `test_count` stays a binary 0/1 from `run_pytest` and the test bar chart + S1 signal read a flag, not a real count, while the aggregate `total_tests` masks it (ARCH-94) contract hole.

- [logging_config.md](logging_config.md) (spec) — `personal_index.logging_config`:
  logging configuration helper (setup_logging/get_logger); setup_logging resolves `level` via `getattr(logging, level.upper(), logging.INFO)` (line 18), so an unknown level string (e.g. "VERBOSE", "TRACE", a typo) is silently coerced to INFO instead of raising, and the existing test pins only valid levels (INFO/DEBUG/WARNING) so the fallback is an untested invariant (ARCH-95) contract hole.

- [pipeline_e2e.md](pipeline_e2e.md) (spec) — `personal_index.pipeline_e2e`:
  end-to-end orchestrator (PipelineE2E: __init__/add_interest/run_from_files/search/close + PipelineRunResult dataclass with success/summary); distinct from pipeline_orchestrator.py (PipelineOrchestrator) and pipeline.py (Pipeline/PipelineRunner); a page that passes the content filter but scores below min_score_threshold is dropped at line 236-237 with NO counter, so pages_filtered_in can exceed pages_indexed with no field explaining the gap and the existing test pins only pages_indexed >= 1 (ARCH-96) contract hole.

- [cli_export.md](cli_export.md) (spec) — `personal_index.cli_export`:
  the standalone `export_cmd` click command (markdown/json/csv/html + --tag/--query/--limit filters) and its private _load_pages/_dispatch_format/_export_* helpers; distinct from cli.py which defines its OWN registered `export` (line 431, markdown/json/csv only, no filters); export_cmd is never imported or registered on the main group (cli.py registers only dedup/health/recommend at lines 1509-1511), so the html format and all three filters are unreachable from the CLI and the module's tests import only the private helpers, never export_cmd (ARCH-98) contract hole.

- [cli_recommend.md](cli_recommend.md) (spec) — `personal_index.cli_recommend`:
  the `recommend` click command (query argument + --top-n/--data-dir/--keyword-weight/--tag-weight/--score-weight) and its private _load_recommender/_print_recommendations helpers; registered on the main group (cli.py:1511); distinct from content_recommender.py which has TWO scoring methods (seed-based recommend(seed,...) honoring all weights, and recommend_for_keywords where tag_weight is a no-op); the CLI wires up ONLY recommend_for_keywords (lines 80/87), so the docstring's "or seed content" clause (line 59) advertises a seed path the command never exposes (ARCH-99) contract hole.

- [cli_top.md](cli_top.md) (spec) — `personal_index.cli_top`:
  the `top_pages` click command (named "top"; --limit/--format/--data-dir) and its private _to_json/_print_text helpers; NEVER imported or registered on the main group (grep for cli_top across the package returns no import), so it is a DEAD parallel implementation of the LIVE inline `top` at cli.py:906; its _to_json emits a hand-built 6-key entry (rank, url, title, score, crawled_at, tags:[]) + top-level total, where tags is a hardcoded always-empty list even though IndexedPage has no tags field, while the live command emits p.to_dict() only (no rank/total/tags) — two incompatible JSON contracts for the same `top` command name (ARCH-100) contract hole.

- [cli_health.md](cli_health.md) (spec) — `personal_index.cli_health`:
  the `health` click command (named "health"; --data-dir/--min-content-length/--min-title-length/--require-tags/--min-score) and its private _load_stores/_build_health_items/_build_config/_print_report/_print_issues/_severity_icon helpers; WIRED (imported at cli.py:27, registered on the main group) so it is the LIVE `health` command; it drives content_health.ContentHealthChecker but exposes only 5 of the 7 ContentHealthCheck knobs — _build_config never sets max_title_length (default 200, gates title_too_long) or min_tags (default 1, gates missing_tags), so two of the seven checks are untunable from the CLI (ARCH-101) contract hole.
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
