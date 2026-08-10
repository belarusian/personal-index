# API Reference

| Module | Export | Description |
|--------|--------|-------------|
| analytics | `SearchEvent` | A search event record. |
| analytics | `CrawlEvent` | A crawl event record. |
| analytics | `AnalyticsData` | Aggregated analytics data. |
| analytics | `AnalyticsTracker` | Track and analyze personal index usage. |
| analytics | `record_search` | Record a search event. |
| analytics | `record_crawl` | Record a crawl event. |
| analytics | `get_analytics` | Compute aggregated analytics. |
| analytics | `get_search_events` | Get search events, optionally limited. |
| analytics | `get_crawl_events` | Get crawl events, optionally limited. |
| analytics | `get_search_stats` | Get detailed search statistics. |
| analytics | `get_crawl_stats` | Get detailed crawl statistics. |
| analytics | `save` | Save analytics data to JSON file. |
| analytics | `load` | Load analytics data from JSON file. Returns total  |
| analytics | `clear` | Clear all tracked events. |
| annotation | `AnnotationType` | [Description] |
| annotation | `Annotation` | A single annotation on content. |
| annotation | `AnnotationStore` | Stores and manages annotations. |
| annotation | `update` | [Description] |
| annotation | `to_dict` | [Description] |
| annotation | `add` | [Description] |
| annotation | `get` | [Description] |
| annotation | `get_by_url` | [Description] |
| annotation | `get_by_type` | [Description] |
| annotation | `update` | [Description] |
| annotation | `remove` | [Description] |
| annotation | `remove_by_url` | [Description] |
| annotation | `search` | Search annotations by URL or value. |
| annotation | `count` | [Description] |
| annotation | `get_stats` | [Description] |
| backup | `BackupManifest` | Manifest describing a backup. |
| backup | `BackupManager` | Manage backups of personal index data. |
| backup | `to_dict` | Convert to dictionary. |
| backup | `from_dict` | Create from dictionary. |
| backup | `create_backup` | Create a backup of the source directory. |
| backup | `list_backups` | List all available backups. |
| backup | `restore_backup` | Restore a backup to the target directory. |
| backup | `delete_backup` | Delete a backup and its archive. |
| backup | `get_backup_info` | Get info about a specific backup. |
| backup | `get_total_backup_size` | Get total size of all backups. |
| backup | `cleanup_old_backups` | Keep only the N most recent backups. Returns delet |
| bookmark_export | `BookmarkExportResult` | Result of a bookmark export operation. |
| bookmark_export | `BookmarkExporter` | Export bookmarks to HTML, JSON, and OPML formats.
 |
| bookmark_export | `export_json` | Export bookmarks as a pretty-printed JSON string.
 |
| bookmark_export | `export_html` | Export bookmarks as Netscape HTML bookmark format. |
| bookmark_export | `export_opml` | Export bookmarks as OPML 2.0 format.

Produces a v |
| bookmark_export | `export` | Export bookmarks in the specified format.

Args:
  |
| bookmark_export | `export_to_file` | Export bookmarks to a file.

Args:
    filepath: D |
| bookmarks | `Bookmark` | A single bookmark entry. |
| bookmarks | `BookmarkManager` | Manage bookmarks for the personal index. |
| bookmarks | `to_dict` | Convert to dictionary. |
| bookmarks | `from_dict` | Create from dictionary. |
| bookmarks | `add` | Add a bookmark, updating if URL already exists. |
| bookmarks | `get` | Get a bookmark by URL. |
| bookmarks | `remove` | Remove a bookmark by URL. Returns True if removed. |
| bookmarks | `list_all` | List all bookmarks. |
| bookmarks | `list_by_category` | List bookmarks in a category. |
| bookmarks | `list_by_tag` | List bookmarks with a specific tag. |
| bookmarks | `list_favorites` | List favorite bookmarks. |
| bookmarks | `toggle_favorite` | Toggle favorite status of a bookmark. |
| bookmarks | `search` | Search bookmarks by title, description, or URL. |
| bookmarks | `get_categories` | Get all unique categories. |
| bookmarks | `get_all_tags` | Get all unique tags. |
| bookmarks | `count` | Count total bookmarks. |
| bookmarks | `save` | Save bookmarks to JSON file. |
| bookmarks | `load` | Load bookmarks from JSON file. Returns count loade |
| cache | `LRUCache` | Thread-safe LRU cache with optional size limit.

U |
| cache | `TTLCache` | Cache with time-to-live expiration.

Each entry ex |
| cache | `CacheDecorator` | Decorator that wraps a function with caching.

Usa |
| cache | `get` | Get value by key, moving it to end (most recently  |
| cache | `put` | Store value in cache, evicting LRU item if at capa |
| cache | `delete` | Remove key from cache.

Args:
    key: Cache key t |
| cache | `clear` | Remove all items from cache. |
| cache | `size` | Current number of items in cache. |
| cache | `hit_rate` | Cache hit rate as a fraction (0.0 to 1.0). |
| cache | `stats` | Return cache statistics. |
| cache | `get` | Get value if not expired.

Args:
    key: Cache ke |
| cache | `put` | Store value with expiration.

Args:
    key: Cache |
| cache | `delete` | Remove key from cache.

Args:
    key: Cache key t |
| cache | `clear` | Remove all items from cache. |
| cache | `size` | Current number of non-expired items. |
| cache | `hit_rate` | Cache hit rate as a fraction. |
| cache | `stats` | Return cache statistics. |
| cache | `wrapper` | [Description] |
| cli | `main` | personal-index - Track and index content matching  |
| cli | `interests` | Manage tracked interests. |
| cli | `add_interest` | Add a new interest to track. |
| cli | `list_interests` | List all tracked interests. |
| cli | `remove_interest` | Remove an interest by name. |
| cli | `toggle_interest` | Toggle an interest on/off. |
| cli | `search` | Search indexed pages. |
| cli | `crawl` | Crawl a URL and index matching content. |
| cli | `index` | Manage the search index. |
| cli | `index_count` | Show number of indexed pages. |
| cli | `index_list` | List indexed pages. |
| cli | `index_clear` | Clear the search index. |
| cli | `schedule` | Manage scheduled crawling jobs. |
| cli | `add_schedule` | Add a scheduled crawl job. |
| cli | `list_schedule` | List scheduled jobs. |
| cli | `remove_schedule` | Remove a scheduled job. |
| cli | `config` | Manage configuration. |
| cli | `config_show` | Show current configuration. |
| cli | `config_set_crawler` | Set crawler configuration. |
| cli | `config_set_schedule` | Set schedule configuration. |
| cli | `get_config_manager` | Get the config manager instance. |
| cli | `save` | [Description] |
| content | `ExtractedContent` | Content extracted from a web page. |
| content | `extract_content` | Extract structured content from HTML. |
| content | `tokenize` | Tokenize text into lowercase words. |
| content | `remove_stopwords` | Remove stopwords from token list. |
| content | `compute_tf` | Compute term frequency for a list of tokens. |
| content | `get_searchable_text` | Get combined searchable text from title, headings, |
| content | `get_keywords` | Extract keywords from meta keywords and headings. |
| content_annotations | `AnnotationType` | Types of annotations users can add to content. |
| content_annotations | `Annotation` | A user annotation on a saved content item. |
| content_annotations | `AnnotationManager` | Manages user annotations on saved content items. |
| content_annotations | `update_text` | Update the annotation text. |
| content_annotations | `add_tag` | Add a tag to this annotation. |
| content_annotations | `remove_tag` | Remove a tag from this annotation. |
| content_annotations | `to_dict` | Serialize to dictionary. |
| content_annotations | `from_dict` | Deserialize from dictionary. |
| content_annotations | `add` | Add an annotation. |
| content_annotations | `get` | Get an annotation by ID. |
| content_annotations | `get_by_content_id` | Get all annotations for a content item. |
| content_annotations | `get_by_author` | Get all annotations by a specific author. |
| content_annotations | `get_by_type` | Get all annotations of a specific type. |
| content_annotations | `get_by_tag` | Get all annotations with a specific tag. |
| content_annotations | `get_all` | Get all annotations. |
| content_annotations | `get_recent` | Get the most recent annotations. |
| content_annotations | `update_text` | Update the text of an annotation. |
| content_annotations | `add_tag` | Add a tag to an annotation. |
| content_annotations | `remove_tag` | Remove a tag from an annotation. |
| content_annotations | `delete` | Delete an annotation. |
| content_annotations | `delete_by_content_id` | Delete all annotations for a content item. Returns |
| content_annotations | `search` | Search annotations by text content. |
| content_annotations | `count` | Return total number of annotations. |
| content_annotations | `get_stats` | Get annotation statistics. |
| content_annotations | `clear` | Remove all annotations. |
| content_annotations | `serialize` | Serialize all annotations to a list of dicts. |
| content_annotations | `deserialize` | Deserialize annotations from a list of dicts. |
| content_categorizer | `TopicCategory` | A topic category with associated keywords and meta |
| content_categorizer | `TopicScore` | Score for a single topic assignment. |
| content_categorizer | `CategorizationResult` | Result of content categorization. |
| content_categorizer | `ContentCategorizer` | Classifies content into topic categories using mul |
| content_categorizer | `secondary_topics` | Return topics after the primary one. |
| content_categorizer | `top_n` | Return top N topics. |
| content_categorizer | `add_topic` | Add or update a topic category.

Args:
    name: T |
| content_categorizer | `remove_topic` | Remove a topic category.

Args:
    name: Topic na |
| content_categorizer | `get_topics` | Get list of all available topic names. |
| content_categorizer | `get_topic` | Get a topic category by name. |
| content_categorizer | `categorize` | Categorize content into topics.

Args:
    text: M |
| content_categorizer | `categorize_batch` | Categorize multiple content items.

Args:
    item |
| content_collections | `Collection` | A collection of saved content items. |
| content_collections | `CollectionManager` | Manages collections of saved content items. |
| content_collections | `add_item` | Add an item to this collection. |
| content_collections | `remove_item` | Remove an item from this collection. |
| content_collections | `contains` | Check if an item is in this collection. |
| content_collections | `item_count` | Return the number of items in this collection. |
| content_collections | `to_dict` | Serialize to dictionary. |
| content_collections | `from_dict` | Deserialize from dictionary. |
| content_collections | `create` | Create a new collection. Returns the collection ID |
| content_collections | `get` | Get a collection by ID. |
| content_collections | `list_all` | List all collections. |
| content_collections | `list_public` | List all public collections. |
| content_collections | `list_private` | List all private collections. |
| content_collections | `get_items` | Get all item IDs in a collection. |
| content_collections | `get_collections_for_item` | Get all collections containing a specific item. |
| content_collections | `add_item` | Add an item to a collection. |
| content_collections | `add_items` | Add multiple items to a collection. |
| content_collections | `remove_item` | Remove an item from a collection. |
| content_collections | `update_name` | Update the name of a collection. |
| content_collections | `update_description` | Update the description of a collection. |
| content_collections | `rename` | Rename a collection (alias for update_name). |
| content_collections | `toggle_public` | Toggle the public/private status of a collection. |
| content_collections | `delete` | Delete a collection. |
| content_collections | `clear_items` | Remove all items from a collection. |
| content_collections | `move_item` | Move an item from one collection to another. |
| content_collections | `merge` | Merge source collection into target collection, de |
| content_collections | `search` | Search collections by name or description. |
| content_collections | `get_recent` | Get the most recently created collections. |
| content_collections | `count` | Return total number of collections. |
| content_collections | `get_stats` | Get collection statistics. |
| content_collections | `serialize` | Serialize all collections to a list of dicts. |
| content_collections | `deserialize` | Deserialize collections from a list of dicts. |
| content_dedup | `SimilarityMethod` | Available similarity detection methods. |
| content_dedup | `DuplicateGroup` | A group of duplicate content items. |
| content_dedup | `DedupResult` | Result of deduplication analysis. |
| content_dedup | `AddItemResult` | Result of adding an item to the deduplicator. |
| content_dedup | `DedupConfig` | Configuration for content deduplication. |
| content_dedup | `ContentDeduplicator` | Detect duplicate or near-duplicate saved content.
 |
| content_dedup | `BatchDedupReport` | Generate a report of deduplication results. |
| content_dedup | `total_count` | Total items in this group (representative + duplic |
| content_dedup | `duplicate_ratio` | Ratio of duplicate items to total items. |
| content_dedup | `find_duplicates` | Find duplicate groups among content items.

Args:
 |
| content_dedup | `add_items` | Add items incrementally and check for duplicates.
 |
| content_dedup | `get_unique_items` | Get unique items, removing duplicates.

Args:
     |
| content_dedup | `clear` | Clear all stored state. |
| content_dedup | `to_dict` | Convert report to dictionary. |
| content_dedup | `to_summary_string` | Generate a human-readable summary. |
| content_enricher | `EnrichedContent` | Content with enriched metadata. |
| content_enricher | `ContentEnricher` | Enrich content with computed metadata and analysis |
| content_enricher | `to_dict` | Convert to dictionary representation. |
| content_enricher | `enrich` | Enrich content with computed metadata.

Args:
     |
| content_enricher | `batch_enrich` | Enrich multiple content items.

Args:
    items: L |
| content_export_csv | `ExportFormat` | Supported export formats. |
| content_export_csv | `ExportStats` | Statistics about an export operation. |
| content_export_csv | `CSVExporter` | Exports content items as CSV and other formats. |
| content_export_csv | `export` | Export items to the specified format. |
| content_export_csv | `export_to_file` | Export items to a file. |
| content_export_csv | `get_stats` | Get export statistics. |
| content_extractor | `ExtractedContent` | Content extracted from an HTML page. |
| content_extractor | `ContentExtractor` | Extracts meaningful content from HTML pages. |
| content_extractor | `extract` | Extract content from HTML string. |
| content_extractor | `extract_readability_score` | Calculate a readability score for extracted conten |
| content_favicon | `FaviconFormat` | Format of the favicon. |
| content_favicon | `FaviconSource` | Source of the favicon. |
| content_favicon | `FaviconStatus` | Status of favicon extraction. |
| content_favicon | `FaviconConfig` | Configuration for favicon extraction. |
| content_favicon | `FaviconInfo` | Information about a favicon. |
| content_favicon | `FaviconResult` | Result of favicon extraction. |
| content_favicon | `FaviconHTMLParser` | Parse HTML to extract favicon links. |
| content_favicon | `FaviconExtractor` | Extract favicons from URLs and HTML content. |
| content_favicon | `FaviconStore` | Store and retrieve favicon results. |
| content_favicon | `FaviconManager` | Manage favicon extraction and caching. |
| content_favicon | `extension` | Get the file extension. |
| content_favicon | `mime_type` | Get the MIME type. |
| content_favicon | `to_dict` | Serialize to dictionary. |
| content_favicon | `from_dict` | Deserialize from dictionary. |
| content_favicon | `to_dict` | Serialize to dictionary. |
| content_favicon | `from_dict` | Deserialize from dictionary. |
| content_favicon | `is_ready` | Check if the favicon is ready. |
| content_favicon | `is_failed` | Check if the extraction failed. |
| content_favicon | `to_dict` | Serialize to dictionary. |
| content_favicon | `from_dict` | Deserialize from dictionary. |
| content_favicon | `handle_starttag` | [Description] |
| content_favicon | `extract_domain` | Extract domain from a URL. |
| content_favicon | `get_favicon_url` | Get the default favicon URL for a given URL. |
| content_favicon | `get_google_favicon_url` | Get favicon URL via Google's favicon service. |
| content_favicon | `extract_from_html` | Extract favicon information from HTML content. |
| content_favicon | `store` | Store a favicon result for a domain. |
| content_favicon | `get` | Get a favicon result for a domain. |
| content_favicon | `contains` | Check if a domain has a stored favicon. |
| content_favicon | `remove` | Remove a favicon result. Returns True if removed. |
| content_favicon | `clear` | Clear all stored favicons. |
| content_favicon | `count` | Get the number of stored favicons. |
| content_favicon | `all_domains` | Get all domains with stored favicons. |
| content_favicon | `to_dict` | Serialize all stored results. |
| content_favicon | `from_dict` | Deserialize from dictionary. |
| content_favicon | `extract_favicon` | Extract favicon for a URL. |
| content_favicon | `batch_extract` | Extract favicons for multiple URLs. |
| content_favicon | `get_cached` | Get a cached favicon result. |
| content_favicon | `refresh_favicon` | Refresh a favicon by re-extracting. |
| content_favicon | `get_summary` | Get a summary of favicon extraction. |
| content_favicon | `clear_cache` | Clear the favicon cache. Returns number of entries |
| content_feed | `FeedFormat` | Supported feed formats. |
| content_feed | `FeedItem` | A single item in a feed. |
| content_feed | `FeedGenerator` | Generates RSS and Atom feeds. |
| content_feed | `to_dict` | Serialize to dictionary. |
| content_feed | `from_dict` | Deserialize from dictionary. |
| content_feed | `add_item` | Add an item to the feed. |
| content_feed | `add_items` | Add multiple items to the feed. |
| content_feed | `clear` | Remove all items from the feed. |
| content_feed | `get_feed_type` | Get the MIME type for a feed format. |
| content_feed | `generate` | Generate feed content in the specified format. |
| content_feed | `to_dict` | Serialize to dictionary. |
| content_feed | `from_dict` | Deserialize from dictionary. |
| content_filter | `FilterConfig` | Configuration for content filtering. |
| content_filter | `ContentFilter` | Filters crawled pages based on interests and confi |
| content_filter | `should_include` | Determine if a page should be included in the inde |
| content_filter | `get_filter_reasons` | Get list of reasons why a page was filtered out. |
| content_filter | `filter_pages` | Filter a list of pages, returning only included on |
| content_health | `check_health` | Run a health check on the content subsystem.

Args |
| content_health | `UrlHealthResult` | Result of checking a single URL's accessibility. |
| content_health | `check_url_accessibility` | Check whether a single URL is still accessible.

U |
| content_health | `check_content_urls` | Check accessibility of all saved content URLs.

It |
| content_health | `to_dict` | Serialize to a plain dict. |
| content_import_html | `HTMLBookmark` | A bookmark imported from Netscape HTML format. |
| content_import_html | `HTMLImportResult` | Result of an HTML bookmark import operation. |
| content_import_html | `HTMLImporter` | Import bookmarks from Netscape HTML bookmark forma |
| content_import_html | `to_dict` | [Description] |
| content_import_html | `from_dict` | [Description] |
| content_import_html | `is_success` | [Description] |
| content_import_html | `to_dict` | [Description] |
| content_import_html | `import_html` | Import bookmarks from Netscape HTML content string |
| content_priority | `PriorityLevel` | Priority levels for content. |
| content_priority | `PriorityScore` | Detailed priority score breakdown. |
| content_priority | `ContentPriority` | A content item with its priority score. |
| content_priority | `PriorityConfig` | Configuration for priority scoring weights. |
| content_priority | `PriorityScorer` | Score content importance based on multiple factors |
| content_priority | `PriorityFilter` | Filter and sort content by priority level. |
| content_priority | `numeric_value` | Numeric value for ordering. |
| content_priority | `from_score` | Convert a numeric score to a priority level. |
| content_priority | `level` | Get the priority level for this score. |
| content_priority | `score` | Score a single content item.

Args:
    content: D |
| content_priority | `score_batch` | Score multiple content items.

Args:
    items: Li |
| content_priority | `rank` | Score and rank content items by priority.

Args:
  |
| content_priority | `filter_by_level` | Filter items to only those meeting minimum priorit |
| content_priority | `get_top_n` | Get the top N highest-priority items.

Args:
    i |
| content_priority | `group_by_level` | Group items by their priority level.

Args:
    it |
| content_scheduler | `ScheduleFrequency` | How often to run a scheduled task. |
| content_scheduler | `ScheduledTask` | A task to be run on a schedule. |
| content_scheduler | `TaskResult` | Result of running a scheduled task. |
| content_scheduler | `ContentScheduler` | Schedule and manage periodic content re-indexing t |
| content_scheduler | `interval_seconds` | [Description] |
| content_scheduler | `mark_run` | Mark the task as having run. |
| content_scheduler | `mark_error` | Record an error from the task. |
| content_scheduler | `is_due` | Check if the task is due to run. |
| content_scheduler | `tasks` | [Description] |
| content_scheduler | `results` | [Description] |
| content_scheduler | `add_task` | Add a new scheduled task. |
| content_scheduler | `remove_task` | Remove a scheduled task by name. |
| content_scheduler | `get_task` | Get a task by name. |
| content_scheduler | `enable_task` | Enable a task. |
| content_scheduler | `disable_task` | Disable a task. |
| content_scheduler | `run_task` | Run a specific task immediately. |
| content_scheduler | `run_due_tasks` | Run all tasks that are due. |
| content_scheduler | `get_due_tasks` | Get all tasks that are due. |
| content_scheduler | `get_enabled_tasks` | Get all enabled tasks. |
| content_scheduler | `get_tasks_by_tag` | Get tasks with a specific tag. |
| content_scheduler | `start` | Start the scheduler in a background thread. |
| content_scheduler | `stop` | Stop the scheduler. |
| content_scheduler | `get_task_stats` | Get statistics about all tasks. |
| content_scheduler | `get_recent_results` | Get the most recent task results. |
| content_scheduler | `clear_results` | Clear all task results. |
| content_scheduler | `reset_task` | Reset a task's run state. |
| content_scoring | `ScoreBreakdown` | Detailed breakdown of content quality scores. |
| content_scoring | `ContentScorer` | Multi-factor content quality scorer.

Evaluates co |
| content_scoring | `score` | Score a content item based on multiple factors.

A |
| content_scoring | `rank` | Rank a list of content items by score (highest fir |
| content_search_fulltext | `Tokenizer` | Tokenizes text into searchable terms. |
| content_search_fulltext | `BM25Ranker` | BM25 ranking algorithm for document scoring. |
| content_search_fulltext | `SearchResult` | A single search result. |
| content_search_fulltext | `SearchResults` | Collection of search results with metadata. |
| content_search_fulltext | `SearchQuery` | A search query with optional filters. |
| content_search_fulltext | `SearchIndex` | Full-text search index with BM25 ranking. |
| content_search_fulltext | `tokenize` | Tokenize text into lowercase words, removing stopw |
| content_search_fulltext | `compute_score` | Compute BM25 score for a document given query toke |
| content_search_fulltext | `to_dict` | Serialize to dictionary. |
| content_search_fulltext | `to_dict` | Serialize to dictionary. |
| content_search_fulltext | `to_dict` | Serialize to dictionary. |
| content_search_fulltext | `from_dict` | Deserialize from dictionary. |
| content_search_fulltext | `add_document` | Add or update a document in the index. |
| content_search_fulltext | `update_document` | Update an existing document. |
| content_search_fulltext | `remove_document` | Remove a document from the index. |
| content_search_fulltext | `search` | Search the index and return ranked results. |
| content_search_fulltext | `search_query` | Search using a SearchQuery object. |
| content_search_fulltext | `get_document` | Get a document by ID. |
| content_search_fulltext | `get_all_ids` | Get all document IDs. |
| content_search_fulltext | `doc_count` | Return the number of indexed documents. |
| content_search_fulltext | `clear` | Clear the entire index. |
| content_search_fulltext | `get_stats` | Get index statistics. |
| content_search_fulltext | `serialize` | Serialize the index. |
| content_search_fulltext | `deserialize` | Deserialize the index. |
| content_social_preview | `SocialPlatform` | Social platform configuration. |
| content_social_preview | `PreviewCardType` | Type of preview card. |
| content_social_preview | `PreviewCardSize` | Size configuration for preview cards. |
| content_social_preview | `PreviewCardStyle` | Visual style for preview cards. |
| content_social_preview | `SocialPreviewStatus` | Status of social preview generation. |
| content_social_preview | `SocialPreviewConfig` | Configuration for social preview generation. |
| content_social_preview | `PreviewCardConfig` | Configuration for preview card generation. |
| content_social_preview | `PreviewCardTemplate` | Template for preview card generation. |
| content_social_preview | `PreviewCardResult` | Result of preview card generation. |
| content_social_preview | `SocialPreviewResult` | Result of social preview generation. |
| content_social_preview | `PreviewCardGenerator` | Generate SVG preview cards. |
| content_social_preview | `PreviewCardManager` | Manage preview card generation and storage. |
| content_social_preview | `SocialPreviewEngine` | High-level engine for social preview generation. |
| content_social_preview | `aspect_ratio` | Calculate the aspect ratio. |
| content_social_preview | `to_dict` | Serialize to dictionary. |
| content_social_preview | `from_dict` | Deserialize from dictionary. |
| content_social_preview | `to_dict` | Serialize to dictionary. |
| content_social_preview | `from_dict` | Deserialize from dictionary. |
| content_social_preview | `get_template` | Get a template by style name. |
| content_social_preview | `is_ready` | Check if the card is ready. |
| content_social_preview | `is_failed` | Check if generation failed. |
| content_social_preview | `to_dict` | Serialize to dictionary. |
| content_social_preview | `from_dict` | Deserialize from dictionary. |
| content_social_preview | `is_ready` | Check if the preview is ready. |
| content_social_preview | `is_failed` | Check if generation failed. |
| content_social_preview | `to_dict` | Serialize to dictionary. |
| content_social_preview | `from_dict` | Deserialize from dictionary. |
| content_social_preview | `generate_card` | Generate an SVG preview card. |
| content_social_preview | `get_cached` | Get a cached card result. |
| content_social_preview | `clear_cache` | Clear the cache. |
| content_social_preview | `create_card` | Create a preview card. |
| content_social_preview | `create_card_batch` | Create cards for multiple items. |
| content_social_preview | `get_card` | Get a card by URL. |
| content_social_preview | `get_summary` | Get a summary of cards. |
| content_social_preview | `generate_preview` | Generate a social preview for a URL. |
| content_social_preview | `generate_card` | Generate a card SVG directly. |
| content_social_preview | `generate_card_batch` | Generate card SVGs for multiple items. |
| content_social_preview | `get_cached` | Get a cached preview. |
| content_social_preview | `get_summary` | Get a summary of previews. |
| content_social_preview | `clear_cache` | Clear the cache. |
| content_summarizer | `KeyPoint` | A key point extracted from content. |
| content_summarizer | `SummaryResult` | Result of content summarization. |
| content_summarizer | `SummaryConfig` | Configuration for summarization. |
| content_summarizer | `ContentSummarizer` | Extract key points from saved articles using extra |
| content_summarizer | `ArticleSummarizer` | High-level API for summarizing articles with metad |
| content_summarizer | `summarize` | Generate a summary with key points from the text.
 |
| content_summarizer | `batch_summarize` | Summarize multiple texts.

Args:
    texts: List o |
| content_summarizer | `summarize_article` | Summarize an article with full metadata.

Args:
   |
| content_summarizer | `summarize_articles` | Summarize multiple articles.

Args:
    articles:  |
| content_thumbnail | `ThumbnailSize` | Thumbnail size configuration. |
| content_thumbnail | `ThumbnailFormat` | Image format for thumbnails. |
| content_thumbnail | `ThumbnailStyle` | Visual style for thumbnails. |
| content_thumbnail | `ThumbnailStatus` | Status of thumbnail generation. |
| content_thumbnail | `ThumbnailConfig` | Configuration for thumbnail generation. |
| content_thumbnail | `ThumbnailMetadata` | Metadata about a generated thumbnail. |
| content_thumbnail | `ThumbnailResult` | Result of thumbnail generation. |
| content_thumbnail | `ThumbnailGenerator` | Generates thumbnail images for saved content. |
| content_thumbnail | `ThumbnailProcessor` | Processes and manages thumbnail generation for mul |
| content_thumbnail | `ThumbnailEngine` | High-level engine for thumbnail operations. |
| content_thumbnail | `area` | Calculate the area of the thumbnail. |
| content_thumbnail | `mime_type` | Get the MIME type for this format. |
| content_thumbnail | `extension` | Get the file extension for this format. |
| content_thumbnail | `to_dict` | Serialize to dictionary. |
| content_thumbnail | `from_dict` | Deserialize from dictionary. |
| content_thumbnail | `is_expired` | Check if the thumbnail metadata has expired. |
| content_thumbnail | `to_dict` | Serialize to dictionary. |
| content_thumbnail | `from_dict` | Deserialize from dictionary. |
| content_thumbnail | `is_ready` | Check if the thumbnail is ready. |
| content_thumbnail | `is_failed` | Check if the thumbnail generation failed. |
| content_thumbnail | `to_dict` | Serialize to dictionary. |
| content_thumbnail | `from_dict` | Deserialize from dictionary. |
| content_thumbnail | `generate_svg_thumbnail` | Generate an SVG thumbnail. |
| content_thumbnail | `generate_thumbnail` | Generate a thumbnail for a URL. |
| content_thumbnail | `get_cached` | Get a cached thumbnail result. |
| content_thumbnail | `clear_cache` | Clear the thumbnail cache. Returns number of entri |
| content_thumbnail | `process_url` | Process a single URL and generate its thumbnail. |
| content_thumbnail | `process_batch` | Process a batch of items. Each item is a dict with |
| content_thumbnail | `get_result` | Get a result by thumbnail ID. |
| content_thumbnail | `get_metadata` | Get metadata for a URL. |
| content_thumbnail | `get_all_results` | Get all results. |
| content_thumbnail | `get_all_metadata` | Get all metadata. |
| content_thumbnail | `get_ready_count` | Count ready thumbnails. |
| content_thumbnail | `get_failed_count` | Count failed thumbnails. |
| content_thumbnail | `get_summary` | Get a summary of processing. |
| content_thumbnail | `to_dict` | Serialize all results and metadata. |
| content_thumbnail | `from_dict` | Deserialize from dictionary. |
| content_thumbnail | `generate` | Generate a thumbnail for a URL. |
| content_thumbnail | `generate_batch` | Generate thumbnails for multiple items. |
| content_thumbnail | `get_svg` | Get SVG thumbnail content directly. |
| content_thumbnail | `get_summary` | Get processing summary. |
| content_thumbnail | `get_metadata` | Get metadata for a URL. |
| content_type | `ContentTypeInfo` | Information about detected content type. |
| content_type | `ContentTypeDetector` | Detects and classifies content types from URLs, fi |
| content_type | `is_downloadable` | Whether this content type should be downloaded. |
| content_type | `detect_from_url` | Detect content type from a URL.

Args:
    url: Th |
| content_type | `detect_from_filename` | Detect content type from a filename.

Args:
    fi |
| content_type | `detect_from_extension` | Detect content type from a file extension.

Args:
 |
| content_type | `detect_from_bytes` | Detect content type from raw bytes (magic number d |
| content_type | `classify` | Classify a MIME type into a category.

Args:
    c |
| content_type | `should_index` | Determine if content at URL should be indexed.

Ar |
| crawl_stats | `DomainStats` | Statistics for a single domain. |
| crawl_stats | `CrawlStats` | Tracks crawl statistics across all domains. |
| crawl_stats | `success_rate` | [Description] |
| crawl_stats | `total_requests` | [Description] |
| crawl_stats | `record_success` | [Description] |
| crawl_stats | `record_failure` | [Description] |
| crawl_stats | `record_skip` | [Description] |
| crawl_stats | `to_dict` | [Description] |
| crawl_stats | `get_domain_stats` | [Description] |
| crawl_stats | `record_url_crawled` | [Description] |
| crawl_stats | `record_url_failed` | [Description] |
| crawl_stats | `record_url_skipped` | [Description] |
| crawl_stats | `uptime` | [Description] |
| crawl_stats | `domain_count` | [Description] |
| crawl_stats | `total_urls` | [Description] |
| crawl_stats | `total_bytes` | [Description] |
| crawl_stats | `error_count` | [Description] |
| crawl_stats | `get_summary` | [Description] |
| crawl_stats | `get_domain_summaries` | [Description] |
| crawl_stats | `reset` | [Description] |
| dedup | `DocumentHash` | Hash representation of a document. |
| dedup | `DeduplicationEngine` | Detect duplicate or near-duplicate content. |
| dedup | `compute_hash` | Compute SHA-256 hash of text. |
| dedup | `compute_fingerprint` | Compute a shorter fingerprint for quick comparison |
| dedup | `from_text` | Create a DocumentHash from page data. |
| dedup | `is_duplicate` | Check if content is a duplicate. Returns (is_dup,  |
| dedup | `is_near_duplicate` | Check for near-duplicates using token overlap. Ret |
| dedup | `duplicate_count` | Number of duplicates detected. |
| dedup | `document_count` | Number of unique documents stored. |
| dedup | `clear` | Clear all stored hashes. |
| dedup | `get_original_url` | Get the original URL for a duplicate. |
| domains | `DomainRule` | Rule for a specific domain. |
| domains | `DomainManager` | Manages domain allow/block rules. |
| domains | `to_dict` | [Description] |
| domains | `from_dict` | [Description] |
| domains | `add_allow` | [Description] |
| domains | `add_block` | [Description] |
| domains | `is_allowed` | [Description] |
| domains | `is_blocked` | [Description] |
| domains | `record_page` | [Description] |
| domains | `get_page_count` | [Description] |
| domains | `reset_counts` | [Description] |
| domains | `remove` | [Description] |
| domains | `list_rules` | [Description] |
| domains | `get_max_depth` | [Description] |
| encoding | `EncodingResult` | Result of encoding detection. |
| encoding | `EncodingDetector` | Detects text encoding and performs conversions. |
| encoding | `detect` | Detect the encoding of byte data. |
| encoding | `decode` | Decode bytes to string, auto-detecting if needed. |
| encoding | `encode` | Encode string to bytes. |
| encoding | `convert` | Convert between encodings. |
| encoding | `normalize_whitespace` | Normalize whitespace in text. |
| encoding | `remove_control_chars` | Remove control characters from text. |
| encoding | `sanitize` | Sanitize text by removing control chars and normal |
| export | `ExportResult` | Result of an export operation. |
| export | `Exporter` | Export bookmarks to various file formats. |
| export | `manager` | [Description] |
| export | `export_to_file` | Export bookmarks to a file, auto-detecting format  |
| export | `export_to_content` | Export bookmarks to a string in the specified form |
| export | `export_filtered` | Export filtered bookmarks to a string. |
| export_markdown | `ExportFormat` | Supported export formats. |
| export_markdown | `ExportConfig` | Configuration for content export. |
| export_markdown | `MarkdownExporter` | Export saved content as markdown, HTML, or plain t |
| export_markdown | `export` | Export content items to the specified format.

Arg |
| formatter | `format_search_results` | Format search results for display. |
| formatter | `format_interest` | Format an interest for display. |
| formatter | `format_crawl_stats` | Format crawl statistics. |
| formatter | `format_index_page` | Format an indexed page for display. |
| formatter | `format_schedule_job` | Format a scheduled job for display. |
| formatter | `format_table` | Format data as a text table. |
| formatter | `format_duration` | Format duration in seconds to human-readable strin |
| formatter | `format_file_size` | Format file size in bytes to human-readable string |
| formatter | `format_timestamp` | Format a timestamp string for display. |
| formatter | `truncate` | Truncate text to max_length, adding ellipsis. |
| formatter | `highlight` | Highlight search terms in text with ** markers. |
| fuzzy_search | `FuzzyMatch` | Result of a fuzzy search match. |
| fuzzy_search | `FuzzySearcher` | Perform fuzzy string matching for search queries. |
| fuzzy_search | `search` | Search for query in a list of texts, returning fuz |
| fuzzy_search | `search_in_dict` | Search in both keys and values of a dictionary. |
| fuzzy_search | `highlight` | Create highlighted version of text with matched in |
| fuzzy_search | `highlight_html` | Create HTML-highlighted version of text. |
| fuzzy_search | `search_with_highlight` | Search and return matches with highlighted text. |
| health | `HealthCheckResult` | Result of a single health check. |
| health | `HealthReport` | Complete health report. |
| health | `HealthChecker` | Run health checks on the personal index system. |
| health | `to_dict` | [Description] |
| health | `to_dict` | [Description] |
| health | `summary` | [Description] |
| health | `run_all` | Run all health checks. |
| health | `check_python_version` | Check Python version compatibility. |
| health | `check_data_directory` | Check data directory exists and is accessible. |
| health | `check_disk_space` | Check available disk space. |
| health | `check_storage_integrity` | Check storage file integrity. |
| health | `check_config_file` | Check configuration file. |
| health | `check_database` | Check SQLite database integrity. |
| health | `check_permissions` | Check file permissions on data directory. |
| health | `check_dependencies` | Check that required dependencies are installed. |
| health_report | `HealthCheckResult` | Result of a single health check. |
| health_report | `HealthReport` | Complete system health report. |
| health_report | `HealthReporter` | Generates comprehensive health reports for the sys |
| health_report | `is_healthy` | True if all checks are healthy. |
| health_report | `is_degraded` | True if any check is degraded but none unhealthy. |
| health_report | `to_dict` | Convert report to dictionary. |
| health_report | `generate_report` | Generate a full health report.

Args:
    extra_ch |
| importer | `ImportResult` | Result of an import operation. |
| importer | `Importer` | Import bookmarks from various file formats. |
| importer | `manager` | [Description] |
| importer | `import_from_file` | Import bookmarks from a file, auto-detecting forma |
| importer | `import_from_content` | Import bookmarks from content string with specifie |
| importer | `import_opml` | Import from OPML format. |
| index | `IndexedPage` | A page stored in the search index. |
| index | `SearchResult` | A result from a search query. |
| index | `SearchIndex` | Search index with SQLite-like persistence via JSON |
| index | `to_dict` | [Description] |
| index | `from_dict` | [Description] |
| index | `add_page` | Add a page to the index. Returns page id. |
| index | `remove_page` | Remove a page from the index. |
| index | `get_page` | Get a page by URL. |
| index | `get_page_count` | Get number of indexed pages. |
| index | `list_pages` | List all pages sorted by score. |
| index | `clear` | Clear the index. |
| index | `search` | Search the index. |
| index | `close` | Close the index (save). |
| indexer | `SearchIndex` | Full-text search index with TF-IDF-like scoring. |
| indexer | `num_documents` | [Description] |
| indexer | `num_terms` | [Description] |
| indexer | `add_page` | Add a page to the index. |
| indexer | `remove_page` | Remove a page from the index. |
| indexer | `search` | Search the index for a query. |
| indexer | `get_page` | Get a page by ID. |
| indexer | `get_all_pages` | Get all indexed pages. |
| indexer | `clear` | Clear the entire index. |
| indexer | `save` | Save index to disk. |
| indexer | `load` | Load index from disk. |
| interest_store | `InterestStore` | Persistent storage for user interests. |
| interest_store | `add` | Add an interest to the store. |
| interest_store | `remove` | Remove an interest by name. Returns True if found  |
| interest_store | `get` | Get an interest by name. |
| interest_store | `list_all` | List all interests, optionally filtering by enable |
| interest_store | `toggle` | Toggle an interest's enabled status. |
| interest_store | `update_priority` | Update an interest's priority (clamped 1-10). |
| interest_store | `matches_any` | Find all interests that match the given text/url. |
| interest_store | `total_score` | Calculate total relevance score across all interes |
| interests | `Interest` | User interest for tracking topics. |
| interests | `InterestStore` | Persistent storage for interests (CLI-facing). |
| interests | `to_dict` | Serialize to dictionary. |
| interests | `from_dict` | Deserialize from dictionary. |
| interests | `add` | Add an interest. |
| interests | `remove` | Remove an interest by name. |
| interests | `get` | Get an interest by name. |
| interests | `list_all` | List all interests. |
| interests | `get_enabled` | List enabled interests. |
| interests | `toggle` | Toggle an interest's enabled status. |
| interests | `get_all_keywords` | Get all keywords from all interests (lowercase). |
| interests | `get_all_url_patterns` | Get all compiled URL patterns. |
| interests | `get_all_topics` | Get all topics from all interests (lowercase). |
| keyword_extractor | `Keyword` | A keyword with its frequency and score. |
| keyword_extractor | `KeywordExtractor` | Extract keywords from text using frequency-based a |
| keyword_extractor | `extract` | Extract keywords from text. |
| keyword_extractor | `extract_phrases` | Extract n-gram phrases from text. |
| keyword_extractor | `extract_top_n` | Extract top N keywords as plain strings. |
| keyword_extractor | `compute_term_frequency` | Compute term frequency for each token in text. |
| keyword_extractor | `compare_keywords` | Compare keywords between two texts, returning shar |
| link_analyzer | `LinkStats` | Statistics about links on a page. |
| link_analyzer | `LinkAnalysisResult` | Result of link analysis. |
| link_analyzer | `LinkAnalyzer` | Analyzes links on crawled pages. |
| link_analyzer | `analyze` | Analyze links found on a page. |
| link_analyzer | `analyze_batch` | Analyze links across multiple pages. |
| link_analyzer | `get_aggregate_stats` | Get aggregate statistics across multiple analyses. |
| link_preview | `LinkPreview` | Structured preview card for a URL, populated from  |
| link_preview | `LinkPreviewGenerator` | Generates LinkPreview cards from HTML content.

Ex |
| link_preview | `generate` | Generate a LinkPreview from HTML content.

Args:
  |
| logging_config | `setup_logging` | Configure logging for the personal_index package. |
| logging_config | `get_logger` | Get a logger for a specific module. |
| metrics | `SystemMetrics` | Snapshot of system metrics. |
| metrics | `MetricsCollector` | Collects and reports system and application metric |
| metrics | `to_dict` | [Description] |
| metrics | `increment_counter` | [Description] |
| metrics | `set_gauge` | [Description] |
| metrics | `record_histogram` | [Description] |
| metrics | `collect_system_metrics` | [Description] |
| metrics | `get_histogram_stats` | [Description] |
| metrics | `get_report` | [Description] |
| metrics | `reset` | [Description] |
| models | `InterestType` | Type of interest to track. |
| models | `Interest` | Represents a user-defined interest to track. |
| models | `CrawlConfig` | Configuration for web crawling behavior. |
| models | `CrawledPage` | A page that has been crawled. |
| models | `IndexedPage` | Represents a crawled and indexed page. |
| models | `SearchResult` | Represents a search result. |
| models | `Page` | A page model for the search index. |
| models | `to_dict` | [Description] |
| models | `from_dict` | [Description] |
| models | `matches` | Check if text/url matches this interest. |
| models | `score` | Calculate relevance score for text. |
| models | `to_dict` | [Description] |
| models | `from_dict` | [Description] |
| models | `to_dict` | [Description] |
| models | `from_dict` | [Description] |
| models | `to_dict` | [Description] |
| models | `from_dict` | [Description] |
| models | `to_dict` | [Description] |
| models | `to_dict` | [Description] |
| models | `from_dict` | [Description] |
| notifications | `NotificationLevel` | Severity levels for notifications. |
| notifications | `NotificationType` | Types of notifications. |
| notifications | `Notification` | A single notification event. |
| notifications | `NotificationHandler` | Abstract base for notification handlers. |
| notifications | `ConsoleHandler` | Print notifications to console. |
| notifications | `FileHandler` | Write notifications to a log file. |
| notifications | `InMemoryHandler` | Store notifications in memory for testing/inspecti |
| notifications | `NotificationManager` | Central notification manager that dispatches to ha |
| notifications | `to_dict` | [Description] |
| notifications | `from_dict` | [Description] |
| notifications | `handle` | Handle a notification. Return True if handled succ |
| notifications | `close` | Clean up resources. |
| notifications | `handle` | [Description] |
| notifications | `close` | [Description] |
| notifications | `handle` | [Description] |
| notifications | `close` | [Description] |
| notifications | `handle` | [Description] |
| notifications | `get_all` | [Description] |
| notifications | `get_unread` | [Description] |
| notifications | `mark_all_read` | [Description] |
| notifications | `clear` | [Description] |
| notifications | `close` | [Description] |
| notifications | `add_handler` | Add a notification handler. |
| notifications | `remove_handler` | Remove a notification handler. |
| notifications | `add_filter` | Add a filter. Notifications passing the filter are |
| notifications | `notify` | Dispatch a notification to all handlers. Returns c |
| notifications | `notify_crawl_complete` | Send a crawl complete notification. |
| notifications | `notify_crawl_error` | Send a crawl error notification. |
| notifications | `notify_new_content` | Send a new content notification. |
| notifications | `notify_interest_match` | Send an interest match notification. |
| notifications | `close` | Close all handlers. |
| pagination | `PageParams` | Parameters for pagination. |
| pagination | `PageResult` | Paginated result set. |
| pagination | `Paginator` | Paginates a collection of items. |
| pagination | `offset` | [Description] |
| pagination | `limit` | [Description] |
| pagination | `total_pages` | [Description] |
| pagination | `has_next` | [Description] |
| pagination | `has_prev` | [Description] |
| pagination | `next_page` | [Description] |
| pagination | `prev_page` | [Description] |
| pagination | `start_index` | [Description] |
| pagination | `end_index` | [Description] |
| pagination | `to_dict` | [Description] |
| pagination | `get_page` | [Description] |
| pagination | `total_items` | [Description] |
| pagination | `total_pages` | [Description] |
| pagination | `iterate_pages` | Get all pages as a list. |
| performance_monitor | `MetricSample` | A single metric data point. |
| performance_monitor | `MetricStats` | Aggregated statistics for a metric. |
| performance_monitor | `PerformanceMonitor` | Monitors and tracks performance metrics. |
| performance_monitor | `TimerContext` | Context manager for timing operations. |
| performance_monitor | `mean` | [Description] |
| performance_monitor | `stddev` | [Description] |
| performance_monitor | `p50` | [Description] |
| performance_monitor | `p95` | [Description] |
| performance_monitor | `p99` | [Description] |
| performance_monitor | `record` | Record a metric value. |
| performance_monitor | `timer` | Create a timer context manager. |
| performance_monitor | `get_stats` | Get aggregated stats for a metric. |
| performance_monitor | `get_all_stats` | Get stats for all tracked metrics. |
| performance_monitor | `reset` | Reset all metrics. |
| performance_monitor | `get_recent_samples` | Get recent samples for a metric. |
| performance_monitor | `elapsed` | [Description] |
| pipeline | `PipelineStep` | A single step in the processing pipeline. |
| pipeline | `PipelineResult` | Result of running a pipeline. |
| pipeline | `ContentPipeline` | Sequential pipeline for processing content through |
| pipeline | `execute` | Execute this step on the data. |
| pipeline | `add_step` | Add a processing step to the pipeline. |
| pipeline | `remove_step` | Remove a step by name. |
| pipeline | `disable_step` | Disable a step by name. |
| pipeline | `enable_step` | Enable a step by name. |
| pipeline | `run` | Run the pipeline on the given data. |
| pipeline | `step_count` | [Description] |
| pipeline | `enabled_steps` | [Description] |
| pipeline | `get_step` | [Description] |
| pipeline | `clear` | [Description] |
| progress | `ProgressState` | States of a progress tracker. |
| progress | `ProgressStep` | A single step within a progress operation. |
| progress | `ProgressTracker` | Track progress of a long-running operation. |
| progress | `ProgressStore` | Store and retrieve progress trackers. |
| progress | `to_dict` | [Description] |
| progress | `progress_percent` | Get progress as percentage (0-100). |
| progress | `elapsed_seconds` | Get elapsed time in seconds. |
| progress | `estimated_remaining` | Estimate remaining time in seconds. |
| progress | `start` | Start the operation. |
| progress | `pause` | Pause the operation. |
| progress | `resume` | Resume a paused operation. |
| progress | `complete` | Mark the operation as completed. |
| progress | `fail` | Mark the operation as failed. |
| progress | `cancel` | Cancel the operation. |
| progress | `advance` | Advance to the next step. |
| progress | `set_total` | Set the total number of steps. |
| progress | `set_message` | Set a status message. |
| progress | `to_dict` | [Description] |
| progress | `from_dict` | Create a ProgressTracker from a dictionary, ignori |
| progress | `format_bar` | Format a progress bar string. |
| progress | `create` | Create a new progress tracker. |
| progress | `get` | Get a tracker by ID. |
| progress | `list_active` | List all active (running/paused) trackers. |
| progress | `list_completed` | List completed trackers, most recent first. |
| progress | `remove` | Remove a tracker. |
| progress | `cleanup` | Remove old completed trackers. Returns count remov |
| progress | `save_all` | Save all trackers to disk. |
| progress | `load_all` | Load trackers from disk. Returns count loaded. |
| queue | `TaskPriority` | [Description] |
| queue | `TaskStatus` | [Description] |
| queue | `Task` | A unit of work in the task queue. |
| queue | `TaskQueue` | Thread-safe priority task queue. |
| queue | `start` | [Description] |
| queue | `complete` | [Description] |
| queue | `fail` | [Description] |
| queue | `cancel` | [Description] |
| queue | `duration` | [Description] |
| queue | `enqueue` | [Description] |
| queue | `dequeue` | [Description] |
| queue | `get_task` | [Description] |
| queue | `cancel_task` | [Description] |
| queue | `complete_task` | [Description] |
| queue | `fail_task` | [Description] |
| queue | `size` | [Description] |
| queue | `pending_count` | [Description] |
| queue | `completed_count` | [Description] |
| queue | `get_stats` | [Description] |
| queue | `clear_completed` | [Description] |
| rate_limiter | `RateLimitConfig` | Configuration for rate limiting. |
| rate_limiter | `RateLimitStatus` | Current status of rate limiting. |
| rate_limiter | `TokenBucket` | Token bucket rate limiter for a single domain. |
| rate_limiter | `RateLimiter` | Rate limiter that manages limits per domain. |
| rate_limiter | `acquire` | Try to acquire a token. Returns True if successful |
| rate_limiter | `wait_time` | Get time to wait before next request can be made. |
| rate_limiter | `status` | Get current rate limit status. |
| rate_limiter | `set_domain_config` | Set rate limit config for a specific domain. |
| rate_limiter | `can_request` | Check if a request to the domain is allowed. |
| rate_limiter | `wait_for_request` | Wait until a request can be made, or timeout. |
| rate_limiter | `get_status` | Get rate limit status for a domain. |
| rate_limiter | `get_wait_time` | Get wait time for a domain. |
| rate_limiter | `reset_domain` | Reset rate limit for a domain. |
| rate_limiter | `reset_all` | Reset all rate limits. |
| rate_limiter | `get_all_statuses` | Get rate limit status for all tracked domains. |
| results | `SearchResult` | A formatted search result. |
| results | `ResultsFormatter` | Formats search results for display. |
| results | `ResultsExporter` | Export search results to various formats. |
| results | `search_and_format` | Search index and format results. |
| results | `format_result` | Format a single search result. |
| results | `format_results` | Format multiple search results. |
| results | `create_snippet` | Create a snippet highlighting the query. |
| results | `to_json` | Export results as JSON. |
| results | `to_csv` | Export results as CSV. |
| results | `to_markdown` | Export results as Markdown. |
| robots_cache | `RobotsCacheEntry` | Cached robots.txt parsing result. |
| robots_cache | `RobotsCache` | Thread-safe cache for robots.txt results. |
| robots_cache | `is_expired` | [Description] |
| robots_cache | `allows_agent` | [Description] |
| robots_cache | `get` | [Description] |
| robots_cache | `put` | [Description] |
| robots_cache | `invalidate` | [Description] |
| robots_cache | `invalidate_all` | [Description] |
| robots_cache | `size` | [Description] |
| robots_cache | `domains` | [Description] |
| robots_cache | `get_stats` | [Description] |
| robots_parser | `RobotsRule` | A single robots.txt rule. |
| robots_parser | `RobotsPolicy` | Parsed robots.txt policy for a domain. |
| robots_parser | `parse_robots_txt` | Parse robots.txt content into a RobotsPolicy. |
| robots_parser | `is_allowed` | Check if a URL is allowed by a robots policy. |
| robots_parser | `can_fetch` | Check if a URL can be fetched according to robots. |
| rss | `FeedEntry` | A single entry from an RSS/Atom feed. |
| rss | `Feed` | A parsed RSS/Atom feed. |
| rss | `RSSParser` | Parse RSS 2.0 and Atom feeds. |
| rss | `to_dict` | Convert to dictionary. |
| rss | `entry_count` | Number of entries in this feed. |
| rss | `get_recent_entries` | Get the most recent entries. |
| rss | `parse` | Parse RSS or Atom feed XML content. |
| rss | `is_feed` | Check if XML content appears to be a feed. |
| scheduler | `ScheduleConfig` | Configuration for a scheduled crawl job. |
| scheduler | `ScheduleEntry` | A scheduled crawl entry. |
| scheduler | `ScheduleStore` | Persistent storage for schedule entries. |
| scheduler | `Scheduler` | Manages scheduled crawling jobs. |
| scheduler | `ScheduledJob` | A scheduled crawl job (CLI-facing). |
| scheduler | `add` | Add a schedule entry. |
| scheduler | `get` | Get a schedule entry by name. |
| scheduler | `remove` | Remove a schedule entry by name. |
| scheduler | `update` | Update a schedule entry. |
| scheduler | `list_all` | List all schedule entries. |
| scheduler | `add_schedule` | Add a new scheduled crawl job. |
| scheduler | `add_job` | Add a scheduled job (alias for add_schedule, CLI-c |
| scheduler | `remove_schedule` | Remove a scheduled crawl job. |
| scheduler | `remove_job` | Remove a scheduled job (alias for remove_schedule, |
| scheduler | `toggle_schedule` | Toggle a schedule's enabled status. |
| scheduler | `get_due_schedules` | Get all schedules that are due to run. |
| scheduler | `update_next_run_times` | Update next_run times based on last_run. |
| scheduler | `run_schedule` | Run a scheduled crawl job. Returns pages indexed. |
| scheduler | `list_jobs` | List all scheduled jobs. |
| scraper | `ScraperConfig` | Configuration for HTML scraping. |
| scraper | `ScrapedContent` | Content extracted from an HTML page. |
| scraper | `HTMLScraper` | Scraps HTML content and extracts structured data. |
| scraper | `scrape` | Scrape HTML content and return structured data. |
| search_index | `SearchIndex` | In-memory search index with JSON persistence. |
| search_index | `add` | Add a page to the index. |
| search_index | `remove` | Remove a page from the index. |
| search_index | `get` | Get a page by URL. |
| search_index | `count` | Return number of indexed pages. |
| search_index | `clear` | Clear the entire index. |
| search_index | `urls` | Return list of all indexed URLs. |
| search_index | `search` | Search and return (url, score) tuples by relevance |
| search_suggestions | `Suggestion` | A single search suggestion. |
| search_suggestions | `SearchSuggestions` | Generates search suggestions from indexed content  |
| search_suggestions | `to_dict` | [Description] |
| search_suggestions | `add_search_history` | Add queries to search history. |
| search_suggestions | `add_tags` | Add tags for suggestion generation. |
| search_suggestions | `add_keywords` | Add extracted keywords for suggestion generation. |
| search_suggestions | `record_search` | Record a single search query. |
| search_suggestions | `get_trending` | Get the most trending search queries. |
| search_suggestions | `suggest` | Generate suggestions for a given prefix. |
| search_suggestions | `get_related_queries` | Get queries related to the given query (from histo |
| search_suggestions | `clear` | Clear all suggestion data. |
| search_suggestions | `to_dict` | Serialize suggestion data. |
| search_suggestions | `from_dict` | Deserialize suggestion data. |
| serializer | `SerializationError` | Raised when serialization fails. |
| serializer | `DeserializationError` | Raised when deserialization fails. |
| serializer | `SerializationConfig` | Configuration for serialization. |
| serializer | `Serializer` | Handles serialization of data to various formats. |
| serializer | `to_json` | Serialize data to JSON string. |
| serializer | `from_json` | Deserialize JSON string to dict. |
| serializer | `to_csv` | Serialize list of dicts to CSV string. |
| serializer | `from_csv` | Deserialize CSV string to list of dicts. |
| serializer | `to_dict` | Convert dataclass or object to dict. |
| session | `SessionStatus` | [Description] |
| session | `SessionStats` | Statistics for a crawl session. |
| session | `CrawlSession` | Represents a single crawl session. |
| session | `SessionManager` | Manages crawl sessions with persistence. |
| session | `success_rate` | [Description] |
| session | `total_processed` | [Description] |
| session | `to_dict` | [Description] |
| session | `duration` | [Description] |
| session | `pause` | [Description] |
| session | `resume` | [Description] |
| session | `complete` | [Description] |
| session | `fail` | [Description] |
| session | `stop` | [Description] |
| session | `record_url_crawled` | [Description] |
| session | `record_url_failed` | [Description] |
| session | `record_url_skipped` | [Description] |
| session | `record_page_indexed` | [Description] |
| session | `to_dict` | [Description] |
| session | `create_session` | [Description] |
| session | `get_session` | [Description] |
| session | `get_active_session` | [Description] |
| session | `set_active` | [Description] |
| session | `list_sessions` | [Description] |
| session | `list_active` | [Description] |
| session | `remove_session` | [Description] |
| session | `save_session` | [Description] |
| session | `load_session` | [Description] |
| session | `session_count` | [Description] |
| similarity | `SimilarityResult` | Result of a similarity comparison. |
| similarity | `SimilarityEngine` | Detects content similarity using multiple algorith |
| similarity | `compare` | Compare two texts for similarity. |
| similarity | `is_similar` | Check if two texts are similar above threshold. |
| similarity | `find_duplicates` | Find duplicate pairs in a list of texts. |
| sitemap | `SitemapEntry` | A single entry from a sitemap. |
| sitemap | `Sitemap` | Parsed sitemap data. |
| sitemap | `SitemapParser` | Parse XML sitemaps and sitemap indexes. |
| sitemap | `is_valid` | Check if the entry has a valid location. |
| sitemap | `url_count` | Number of URLs in this sitemap. |
| sitemap | `sitemap_count` | Number of nested sitemaps. |
| sitemap | `get_urls` | Get all URLs from entries. |
| sitemap | `parse` | Parse sitemap XML content. |
| sitemap | `parse_text_sitemap` | Parse a plain text sitemap (one URL per line). |
| sitemap | `filter_by_priority` | Filter sitemap entries by minimum priority. |
| sitemap | `filter_by_changefreq` | Filter sitemap entries by change frequency. |
| sitemap | `get_recent_entries` | Get entries modified within the last N days. |
| sitemap_builder | `SitemapEntry` | Represents a single URL entry in a sitemap. |
| sitemap_builder | `SitemapBuilder` | Builds XML sitemap from a collection of URLs. |
| sitemap_builder | `to_element` | [Description] |
| sitemap_builder | `add_entry` | [Description] |
| sitemap_builder | `add_entries` | [Description] |
| sitemap_builder | `build` | Build the complete sitemap XML as bytes. |
| sitemap_builder | `build_sitemap_index` | Build a sitemap index file referencing multiple si |
| sitemap_builder | `split_into_chunks` | Split entries into chunks for multiple sitemap fil |
| sitemap_builder | `clear` | [Description] |
| sitemap_builder | `url_count` | [Description] |
| stats | `IndexStats` | Statistics about the search index. |
| stats | `CrawlStats` | Statistics about crawling activity. |
| stats | `StatsCollector` | Collects and reports statistics. |
| stats | `get_index_stats` | Calculate current index statistics. |
| stats | `format_index_stats` | Format index statistics as a string. |
| storage | `Storage` | File-based storage for interests, config, and inde |
| storage | `add_interest` | Add a new interest. |
| storage | `get_interests` | Get all interests. |
| storage | `get_interest` | Get a single interest by name. |
| storage | `remove_interest` | Remove an interest by name. |
| storage | `list_interests` | List all interests with summary info. |
| storage | `save_config` | Save crawl configuration. |
| storage | `get_config` | Get crawl configuration. |
| storage | `add_page` | Add or update an indexed page. |
| storage | `get_pages` | Get all indexed pages. |
| storage | `get_page` | Get a single page by URL. |
| storage | `remove_page` | Remove a page by URL. |
| storage | `get_page_count` | Get total number of indexed pages. |
| storage | `clear_pages` | Clear all indexed pages. |
| storage | `get_stats` | Get storage statistics. |
| summarizer | `SummaryResult` | Result of content summarization. |
| summarizer | `TextSummarizer` | Extractive text summarization using various method |
| summarizer | `summarize` | Generate a summary of the text. |
| summarizer | `truncate` | Truncate text to a maximum length. |
| tags | `Tag` | A tag that can be applied to pages. |
| tags | `TagStore` | Persistent storage for tags and their page associa |
| tags | `create_tag` | Create a new tag. |
| tags | `get_tag` | Get a tag by name. |
| tags | `list_tags` | List all tags. |
| tags | `delete_tag` | Delete a tag and remove it from all pages. |
| tags | `add_tag_to_page` | Add a tag to a page. Returns False if tag doesn't  |
| tags | `remove_tag_from_page` | Remove a tag from a page. |
| tags | `get_tags_for_page` | Get all tags for a page. |
| tags | `get_pages_for_tag` | Get all pages with a specific tag. |
| tags | `search_by_tag` | Search for pages by tag name (alias for get_pages_ |
| tags | `get_tag_count` | Get total number of tags. |
| tags | `get_tagged_page_count` | Get number of pages that have at least one tag. |
| tags | `clear` | Clear all tags and associations. |
| text_utils | `normalize_whitespace` | Collapse all whitespace sequences into single spac |
| text_utils | `remove_html_tags` | Strip HTML tags from text, preserving content.

Ar |
| text_utils | `truncate_text` | Truncate text to a maximum length without breaking |
| text_utils | `extract_sentences` | Split text into sentences.

Args:
    text: Input  |
| text_utils | `extract_paragraphs` | Split text into paragraphs.

Args:
    text: Input |
| text_utils | `word_frequency` | Calculate word frequency in text.

Args:
    text: |
| text_utils | `extract_keywords` | Extract top keywords from text by frequency.

Args |
| text_utils | `levenshtein_distance` | Calculate Levenshtein edit distance between two st |
| text_utils | `similarity_ratio` | Calculate similarity ratio between two strings (0. |
| text_utils | `slugify` | Convert text to URL-friendly slug.

Args:
    text |
| text_utils | `highlight_text` | Highlight search terms in text.

Args:
    text: I |
| text_utils | `count_words` | Count words in text.

Args:
    text: Input text.
 |
| text_utils | `count_characters` | Count characters in text.

Args:
    text: Input t |
| text_utils | `read_time_minutes` | Estimate reading time in minutes.

Args:
    text: |
| text_utils | `tokenize` | Tokenize text into words.

Args:
    text: Input t |
| tfidf | `TfidfScorer` | Compute TF-IDF scores for documents and queries. |
| tfidf | `add_document` | Add a document to the corpus. Returns document ID. |
| tfidf | `remove_document` | Remove a document from the corpus. |
| tfidf | `compute_tfidf` | Compute TF-IDF scores for a document. |
| tfidf | `score_query` | Score a document against a query using TF-IDF dot  |
| tfidf | `rank_documents` | Rank all documents by relevance to query. |
| tfidf | `document_count` | Return number of documents in corpus. |
| tfidf | `vocabulary_size` | Return size of vocabulary. |
| tfidf | `get_top_terms` | Get top N terms by TF-IDF score for a document. |
| tfidf | `clear` | Clear the corpus. |
| throttle | `ThrottleRule` | Rate limiting rule for a domain. |
| throttle | `ThrottleState` | Tracks throttle state for a domain. |
| throttle | `ThrottleManager` | Manages request throttling across multiple domains |
| throttle | `rate_per_second` | [Description] |
| throttle | `set_rule` | [Description] |
| throttle | `get_rule` | [Description] |
| throttle | `should_throttle` | [Description] |
| throttle | `wait_if_needed` | Wait if throttling is needed, return wait time in  |
| throttle | `get_stats` | [Description] |
| throttle | `reset` | [Description] |
| url_classifier | `URLCategory` | [Description] |
| url_classifier | `ClassificationResult` | Result of URL classification. |
| url_classifier | `URLClassifier` | Classifies URLs into categories based on patterns. |
| url_classifier | `classify` | Classify a URL into a category. |
| url_classifier | `classify_batch` | Classify multiple URLs. |
| url_classifier | `get_category_counts` | Get count of URLs per category. |
| url_classifier | `api_re` | [Description] |
| url_classifier | `media_re` | [Description] |
| url_classifier | `feed_re` | [Description] |
| url_classifier | `static_re` | [Description] |
| url_classifier | `redirect_re` | [Description] |
| url_dedup | `DedupResult` | Result of deduplication check. |
| url_dedup | `URLDeduplicator` | Deduplicate URLs using normalization and fuzzy mat |
| url_dedup | `seen_count` | [Description] |
| url_dedup | `normalize_url` | Normalize a URL for comparison. |
| url_dedup | `check_duplicate` | Check if a URL is a duplicate of a previously seen |
| url_dedup | `add_url` | Add a URL and check if it's a duplicate. |
| url_dedup | `deduplicate_urls` | Deduplicate a list of URLs, returning unique URLs  |
| url_dedup | `get_duplicates` | Get all detected duplicates grouped by canonical U |
| url_dedup | `get_stats` | Get deduplication statistics. |
| url_dedup | `clear` | Clear all seen URLs. |
| url_dedup | `get_canonical_url` | Get the canonical (first seen) URL for a given URL |
| url_dedup | `get_domain_urls` | Get all URLs for a specific domain. |
| url_filter | `UrlFilterRule` | A single URL filter rule. |
| url_filter | `UrlFilter` | Filter URLs based on blacklist and whitelist rules |
| url_filter | `matches` | Check if URL matches this rule's pattern. |
| url_filter | `add_blacklist` | Add a URL pattern to the blacklist. |
| url_filter | `add_whitelist` | Add a URL pattern to the whitelist. |
| url_filter | `is_allowed` | Check if a URL is allowed (passes all filters).

A |
| url_filter | `is_blocked` | Check if a URL is blocked.

Args:
    url: URL to  |
| url_filter | `filter_urls` | Filter a list of URLs, returning only allowed ones |
| url_filter | `get_blocked_urls` | Return URLs that are blocked.

Args:
    urls: Lis |
| url_filter | `get_matching_rule` | Get the first matching rule for a URL, or None.

A |
| url_filter | `blacklist_count` | Number of blacklist rules. |
| url_filter | `whitelist_count` | Number of whitelist rules. |
| url_filter | `clear` | Clear all rules. |
| url_filter | `clear_blacklist` | Clear all blacklist rules. |
| url_filter | `clear_whitelist` | Clear all whitelist rules. |
| url_history | `URLVisit` | Record of a single URL visit. |
| url_history | `URLHistory` | Track URL visit history with persistence. |
| url_history | `to_dict` | [Description] |
| url_history | `from_dict` | [Description] |
| url_history | `record` | Record a URL visit. |
| url_history | `get_visits` | Get visit records, optionally filtered by URL and  |
| url_history | `get_unique_urls` | Get list of unique URLs visited. |
| url_history | `get_stats` | Get statistics about URL history. |
| url_history | `get_domain_stats` | Get visit counts grouped by domain. |
| url_history | `clear` | Clear all history. Returns count of cleared entrie |
| url_history | `save` | Save history to file. |
| url_history | `load` | Load history from file. Returns count loaded. |
| url_normalizer | `normalize_url` | Normalize a URL by applying standard transformatio |
| url_normalizer | `is_canonical` | Check if a URL is already in canonical form. |
| url_normalizer | `get_domain` | Extract the domain from a URL. |
| url_normalizer | `get_path` | Extract the path from a URL. |
| url_normalizer | `get_query_string` | Extract the query string from a URL. |
| url_normalizer | `get_fragment` | Extract the fragment from a URL. |
| url_normalizer | `urls_are_equivalent` | Check if two URLs are equivalent after normalizati |
| url_normalizer | `strip_tracking_params` | Remove common tracking parameters from a URL. |
| url_normalizer | `resolve_relative_url` | Resolve a relative URL against a base URL. |
| url_utils | `is_valid_url` | Check if a URL is valid and has an http/https sche |
| url_utils | `normalize_url` | Normalize URL: lowercase scheme/domain, remove fra |
| url_utils | `extract_domain` | Extract domain from URL. |
| url_utils | `extract_subdomain` | Extract subdomain from URL. |
| url_utils | `get_tld` | Extract top-level domain from URL. |
| url_utils | `is_same_domain` | Check if two URLs are on the same domain. |
| url_utils | `is_internal_link` | Check if URL is an internal link relative to base  |
| url_utils | `remove_query_params` | Remove specific query parameters from URL. |
| url_utils | `url_to_path` | Convert URL to a filesystem-safe path. |
| url_utils | `join_urls` | Join a base URL with a relative URL.

If base ends |
| url_utils | `extract_all_urls` | Extract all URLs from HTML content or plain text.
 |
| url_utils | `is_robotstxt` | Check if URL is a robots.txt file. |
| url_utils | `is_sitemap` | Check if URL is a sitemap file. |
| url_utils | `is_excluded_url` | Check if URL should be excluded from crawling. |
| validator | `ValidationResult` | Result of a validation check. |
| validator | `URLValidator` | Validates URLs for crawling. |
| validator | `ContentValidator` | Validates extracted content quality. |
| validator | `add_error` | [Description] |
| validator | `add_warning` | [Description] |
| validator | `validate` | [Description] |
| validator | `validate_batch` | Validate multiple URLs. |
| validator | `validate` | [Description] |
| versioning | `ContentVersion` | A versioned snapshot of content. |
| versioning | `VersionTracker` | Tracks content versions and detects changes. |
| versioning | `to_dict` | [Description] |
| versioning | `compute_hash` | Compute SHA-256 hash of content. |
| versioning | `generate_version_id` | Generate a unique version ID from URL and content  |
| versioning | `record_version` | Record a new version of content for a URL. |
| versioning | `get_versions` | Get all versions for a URL. |
| versioning | `get_latest` | Get the latest version for a URL. |
| versioning | `has_changed` | Check if new content differs from the latest versi |
| versioning | `get_change_count` | Get the number of version changes for a URL. |
| versioning | `get_all_urls` | Get all tracked URLs. |
| versioning | `clear` | Clear versions for a URL or all URLs. |
| versioning | `total_versions` | Total number of versions tracked. |
| versioning | `tracked_urls` | Number of URLs being tracked. |
| webhook | `WebhookEvent` | [Description] |
| webhook | `WebhookPayload` | Payload sent to webhook endpoints. |
| webhook | `WebhookConfig` | Configuration for a webhook endpoint. |
| webhook | `WebhookSender` | Sends webhook notifications to configured endpoint |
| webhook | `to_dict` | [Description] |
| webhook | `to_json` | [Description] |
| webhook | `should_send` | [Description] |
| webhook | `add_endpoint` | [Description] |
| webhook | `remove_endpoint` | [Description] |
| webhook | `send` | Send a webhook payload to all matching endpoints. |
| webhook | `endpoint_count` | [Description] |
| detector | `TopicDetector` | Detects topics in text content using keyword match |
| detector | `detect` | Detect topics in the given text. |
| detector | `add_topic` | Add a custom topic definition. |
| detector | `remove_topic` | Remove a topic definition. |
| detector | `get_all_topics` | Return all registered topic names. |
| tag | `Tag` | Represents a detected topic tag with confidence sc |
| tag | `to_dict` | [Description] |
| tag | `from_dict` | [Description] |
| tagger | `TagResult` | Result of tagging content. |
| tagger | `ContentTagger` | High-level interface for tagging content by detect |
| tagger | `to_dict` | [Description] |
| tagger | `from_dict` | [Description] |
| tagger | `tag` | Tag content by detecting topics. |
| tagger | `batch_tag` | Tag multiple pieces of content. |
| tagger | `get_tag_statistics` | Return tag usage statistics. |
| tagger | `add_topic` | Add a custom topic to the detector. |
| tagger | `clear_statistics` | Clear tag usage statistics. |
| 001_initial_schema | `up` | Create initial schema. |
| 001_initial_schema | `down` | Drop initial schema. |
| 002_add_indexes | `up` | Add indexes and bookmarks table. |
| 002_add_indexes | `down` | Drop indexes and bookmarks table. |
| base | `MigrationRecord` | Record of an applied migration. |
| base | `MigrationStatus` | Current migration status. |
| base | `BaseMigration` | Abstract base class for database migrations. |
| base | `MigrationRegistry` | Registry that discovers and manages migration clas |
| base | `MigrationStore` | Stores migration history (in-memory or file-based) |
| base | `to_dict` | [Description] |
| base | `to_dict` | [Description] |
| base | `upgrade` | Apply the migration. Returns list of operations pe |
| base | `downgrade` | Rollback the migration. Returns list of operations |
| base | `validate` | Validate the migration can be applied. Returns lis |
| base | `module_name` | [Description] |
| base | `register` | Register a migration class. |
| base | `get_migration` | Get a migration class by version. |
| base | `get_all_versions` | Get all registered migration versions in order. |
| base | `get_pending` | Get migrations that haven't been applied yet. |
| base | `get_applied` | Get migrations that have been applied. |
| base | `record_applied` | Record that a migration was applied. |
| base | `get_applied_versions` | Get list of applied migration versions. |
| base | `get_record` | Get migration record by version. |
| base | `remove_record` | Remove a migration record (for rollback). |
| base | `get_current_version` | Get the current schema version. |
| runner | `MigrationRunner` | Runs migrations against a migration store. |
| runner | `MigrationError` | Error during migration execution. |
| runner | `run_pending` | Run all pending migrations.

Args:
    dry_run: If |
| runner | `rollback` | Rollback applied migrations.

Args:
    steps: Num |
| runner | `get_status` | Get current migration status. |
| runner | `validate_all` | Validate all pending migrations without applying.
 |
| __init__ | `Interest` | An interest to track. |
| __init__ | `CrawlConfig` | Crawler configuration. |
| __init__ | `SchedulerConfig` | Scheduler configuration. |
| __init__ | `AppConfig` | Application configuration. |
| __init__ | `ConfigManager` | Manages loading and saving configuration. |
| __init__ | `to_dict` | [Description] |
| __init__ | `from_dict` | [Description] |
| __init__ | `to_dict` | [Description] |
| __init__ | `from_dict` | [Description] |
| __init__ | `to_dict` | [Description] |
| __init__ | `from_dict` | [Description] |
| __init__ | `to_dict` | [Description] |
| __init__ | `from_dict` | [Description] |
| __init__ | `save` | Save config to disk. |
| __init__ | `load` | Load config from disk. |
| __init__ | `load` | Load config, creating default if file doesn't exis |
| __init__ | `save` | Save config to disk. |
| __init__ | `add_interest` | Add an interest to the config. |
| __init__ | `remove_interest` | Remove an interest by topic. |
| __init__ | `get_interest` | Get an interest by topic. |
| loader | `load_config` | Load configuration from YAML file. |
| loader | `save_config` | Save configuration to YAML file. |
| loader | `create_default_config` | Create a default configuration file. |
| models | `MatchMode` | How keywords should be matched. |
| models | `Interest` | User interest configuration. |
| models | `CrawlerConfig` | Crawler configuration. |
| models | `SchedulerConfig` | Scheduler configuration. |
| models | `IndexConfig` | Index configuration. |
| models | `AppConfig` | Top-level application configuration. |
| api_keys | `APIKey` | Represents an API key with metadata. |
| api_keys | `APIKeyStore` | In-memory store for API keys with CRUD operations. |
| api_keys | `validate_api_key` | Convenience function to validate an API key.

Args |
| api_keys | `to_dict` | [Description] |
| api_keys | `create_key` | Create a new API key.

Args:
    owner: Key owner  |
| api_keys | `validate_key` | Validate an API key and return its metadata if val |
| api_keys | `revoke_key` | Revoke an API key.

Args:
    key_id: The key ID t |
| api_keys | `get_key` | Get API key metadata by ID.

Args:
    key_id: The |
| api_keys | `list_keys` | List API keys, optionally filtered by owner.

Args |
| api_keys | `delete_key` | Permanently delete an API key.

Args:
    key_id:  |
| passwords | `PasswordConfig` | Configuration for password hashing. |
| passwords | `hash_password` | Hash a password with a random salt.

The returned  |
| passwords | `verify_password` | Verify a password against a hashed password.

Args |
| passwords | `is_valid_password` | Validate password strength.

Args:
    password: T |
| permissions | `Permission` | Built-in permissions for the system. |
| permissions | `Role` | Built-in roles with predefined permission sets. |
| permissions | `User` | Represents a user with roles and permissions. |
| permissions | `PermissionChecker` | Checks if a user has specific permissions. |
| permissions | `get_permissions` | Get all permissions for this user. |
| permissions | `check` | Check if a user has a specific permission.

Args:
 |
| permissions | `check_any` | Check if user has any of the given permissions.

A |
| permissions | `check_all` | Check if user has all of the given permissions.

A |
| permissions | `add_role_permissions` | Add custom permissions to a role.

Args:
    role: |
| permissions | `get_role_permissions` | Get permissions for a role.

Args:
    role: The r |
| sessions | `Session` | Represents an active user session. |
| sessions | `SessionStore` | In-memory session store with expiration support. |
| sessions | `to_dict` | [Description] |
| sessions | `is_expired` | Check if the session has expired. |
| sessions | `create_session` | Create a new session for a user.

Args:
    user_i |
| sessions | `get_session` | Get a session by ID, updating last accessed time.
 |
| sessions | `update_session` | Update session data and optionally extend TTL.

Ar |
| sessions | `destroy_session` | Destroy a session.

Args:
    session_id: The sess |
| sessions | `destroy_user_sessions` | Destroy all sessions for a user.

Args:
    user_i |
| sessions | `get_active_count` | Get count of active sessions.

Args:
    user_id:  |
| sessions | `cleanup_expired` | Remove all expired sessions.

Returns:
    Number  |
| tokens | `TokenPayload` | Payload data embedded in a JWT token. |
| tokens | `JWTManager` | Manages JWT token creation and verification using  |
| tokens | `generate_token` | Convenience function to generate a JWT token.

Arg |
| tokens | `verify_token` | Convenience function to verify a JWT token.

Args: |
| tokens | `to_dict` | [Description] |
| tokens | `from_dict` | [Description] |
| tokens | `create_token` | Create a new JWT token.

Args:
    subject: User i |
| tokens | `verify_token` | Verify and decode a JWT token.

Args:
    token: T |
| tokens | `blacklist_token` | Blacklist a token to prevent reuse.

Args:
    tok |
| facet | `FacetType` | Type of facet dimension. |
| facet | `FacetValue` | A single value within a facet. |
| facet | `Facet` | A filterable search dimension with values. |
| facet | `to_dict` | [Description] |
| facet | `from_dict` | [Description] |
| facet | `add_value` | Add or update a facet value. |
| facet | `sort_values` | Sort values by count descending. |
| facet | `to_dict` | [Description] |
| facet | `from_dict` | [Description] |
| facet_builder | `FacetBuilder` | Builds facet dimensions from a collection of docum |
| facet_builder | `build` | Build facets from a list of document items. |
| facet_builder | `aggregate` | Aggregate two facet dictionaries. |
| faceted_search | `SearchResults` | Container for faceted search results. |
| faceted_search | `FacetedSearch` | Search engine with filterable facet dimensions. |
| faceted_search | `keys` | Return available keys. |
| faceted_search | `to_dict` | [Description] |
| faceted_search | `add_document` | Add a document to the search index. |
| faceted_search | `remove_document` | Remove a document from the search index. |
| faceted_search | `get_documents` | Get all indexed documents. |
| faceted_search | `get_available_facets` | Get list of available facet fields. |
| faceted_search | `search` | Search with optional filters and facets. |
| faceted_search | `clear` | Clear all documents. |
| __init__ | `CrawlerConfig` | Configuration for the web crawler. |
| __init__ | `Crawler` | Web crawler with depth control and politeness. |
| __init__ | `WebCrawler` | High-level web crawler interface for integration t |
| __init__ | `to_dict` | [Description] |
| __init__ | `from_dict` | [Description] |
| __init__ | `pages_crawled` | [Description] |
| __init__ | `results` | [Description] |
| __init__ | `crawl` | Crawl starting from seed URLs. |
| __init__ | `close` | Close the crawler session. |
| __init__ | `crawl` | Crawl starting from seed URLs and return Page obje |
| __init__ | `close` | Close the crawler session. |
| main | `CrawlerConfig` | Configuration for the web crawler. |
| main | `Crawler` | Web crawler with depth control and politeness. |
| main | `pages_crawled` | [Description] |
| main | `results` | [Description] |
| main | `crawl` | Start crawling from seed URLs. |
| main | `close` | Close the crawler session. |
| robots | `RobotsRule` | A single robots.txt rule. |
| robots | `RobotsPolicy` | Parsed robots.txt policy for a domain. |
| robots | `parse_robots_txt` | Parse robots.txt content into a RobotsPolicy. |
| robots | `is_allowed` | Check if URL is allowed by robots policy. |
| robots | `RobotsParser` | Simple robots.txt parser. |
| robots | `can_fetch` | Check if a URL can be fetched. |
| robots | `parse` | Parse robots.txt text. |
| robots | `can_fetch` | Check if URL can be fetched. |
| archive_entry | `ArchiveStatus` | Status of an archived content item. |
| archive_entry | `ArchiveEntry` | Represents a content item in the archive system. |
| archive_entry | `archive` | Mark this entry as archived. |
| archive_entry | `restore` | Restore this entry to active status. |
| archive_entry | `delete` | Mark this entry as deleted. |
| archive_entry | `to_dict` | [Description] |
| archive_entry | `from_dict` | [Description] |
| archiver | `ArchiveConfig` | Configuration for the archiver. |
| archiver | `ContentArchiver` | Manages archiving of old content items. |
| archiver | `format` | [Description] |
| archiver | `add_item` | Add a content item to the archiver. |
| archiver | `get_item` | Get an item by ID. |
| archiver | `remove_item` | Remove an item. |
| archiver | `archive_old` | Archive items older than the threshold. |
| archiver | `restore_item` | Restore an archived item. |
| archiver | `get_archived_items` | Get all archived items. |
| archiver | `delete_archived` | Delete all archived items. |
| archiver | `get_stats` | Get archive statistics. |
| archiver | `export_archived` | Export archived items to a JSON file. |
| compressor | `CompressionFormat` | Supported compression formats. |
| compressor | `Compressor` | Handles compression and decompression of content. |
| compressor | `compress` | Compress raw bytes data. |
| compressor | `decompress` | Decompress raw bytes data. |
| compressor | `compress_text` | Compress a text string. |
| compressor | `decompress_text` | Decompress bytes back to text string. |
| compressor | `compression_ratio` | Calculate compression ratio (1.0 = no compression, |
| compressor | `get_stats` | Get compression statistics. |
| __init__ | `extract_links` | Extract all valid links from HTML content. |
| __init__ | `extract_title` | Extract page title from HTML. |
| __init__ | `extract_meta_description` | Extract meta description from HTML. |
| __init__ | `extract_text_content` | Extract text content from HTML, removing scripts a |
| __init__ | `tokenize` | Tokenize text into lowercase words. |
| __init__ | `compute_relevance_score` | Compute relevance score of text against keywords. |
| url_utils | `is_valid_url` | Check if URL is valid with http/https scheme. |
| url_utils | `normalize_url` | Normalize URL: lowercase domain, remove fragments, |
| url_utils | `resolve_relative_url` | Resolve a relative URL against a base URL. |
| url_utils | `extract_domain` | Extract domain from URL, stripping port number. |
| url_utils | `is_excluded_url` | Check if URL should be excluded from crawling. |
| url_utils | `get_url_depth` | Get the depth of a URL path. |
| url_utils | `is_same_domain` | Check if two URLs are on the same domain. |
| aggregator | `TimeSeriesPoint` | A single point in a time series. |
| aggregator | `AggregatedStats` | Aggregated statistics for the dashboard. |
| aggregator | `DashboardAggregator` | Aggregates data from index instances for dashboard |
| aggregator | `to_dict` | [Description] |
| aggregator | `to_dict` | [Description] |
| aggregator | `aggregate` | Aggregate statistics from available data sources.
 |
| aggregator | `clear_cache` | Clear the stats cache. |
| export | `ExportFormat` | Supported export formats. |
| export | `ExportResult` | Result of an export operation. |
| export | `DashboardExporter` | Exports dashboard data in various formats. |
| export | `to_dict` | [Description] |
| export | `export_stats` | Export aggregated stats to a format.

Args:
    st |
| export | `export_pages` | Export pages list to a format.

Args:
    pages: L |
| export | `export_time_series` | Export time series data.

Args:
    series: List o |
| stats | `RealTimeStats` | Real-time operational statistics for the dashboard |
| stats | `to_dict` | [Description] |
| views | `DashboardStat` | A single dashboard statistic. |
| views | `DashboardSection` | A section of the dashboard. |
| views | `DashboardData` | Complete dashboard data model. |
| views | `escape` | Escape HTML special characters. |
| views | `render_dashboard_html` | Render dashboard data as HTML.

Args:
    data: Da |
| views | `build_dashboard` | Build dashboard data from index instances.

Args:
 |
| views | `to_dict` | [Description] |
| views | `to_dict` | [Description] |
| views | `to_dict` | [Description] |
| handlers | `ErrorHandler` | ASGI middleware that catches API exceptions and re |
| handlers | `TimingMiddleware` | Middleware that adds response timing headers. |
| handlers | `ContentTypeMiddleware` | Middleware that ensures JSON content-type for API  |
| handlers | `handle_api_error` | Convert an exception to an API response.

Args:
   |
| handlers | `timed_send` | [Description] |
| handlers | `ensure_json_type` | [Description] |
| middleware | `RequestLoggingMiddleware` | Middleware that logs all incoming requests. |
| middleware | `CORSHeadersMiddleware` | Middleware that adds CORS headers to responses. |
| middleware | `RequestIdMiddleware` | Middleware that assigns a unique request ID to eac |
| middleware | `create_middleware_stack` | Create a stack of middleware for the application.
 |
| middleware | `capture_send` | [Description] |
| middleware | `add_cors_headers` | [Description] |
| middleware | `add_request_id` | [Description] |
| models | `APIResponse` | Standard API response wrapper. |
| models | `PaginatedResponse` | Paginated response with metadata. |
| models | `SearchRequest` | Search request parameters. |
| models | `SearchResponse` | Search response with results. |
| models | `ErrorResponse` | Error response with details. |
| models | `APIError` | Base API exception. |
| models | `NotFoundError` | Resource not found. |
| models | `ValidationError` | Request validation failed. |
| models | `UnauthorizedError` | Authentication required. |
| models | `ForbiddenError` | Permission denied. |
| models | `to_dict` | [Description] |
| models | `ok` | [Description] |
| models | `error` | [Description] |
| models | `total_pages` | [Description] |
| models | `to_dict` | [Description] |
| models | `validate` | [Description] |
| models | `to_dict` | [Description] |
| models | `to_dict` | [Description] |
| pagination | `PageInfo` | Pagination metadata. |
| pagination | `PaginatedResult` | A paginated result set. |
| pagination | `paginate` | Paginate a sequence of items.

Args:
    items: Th |
| pagination | `paginate_with_offset` | Paginate using offset/limit instead of page number |
| pagination | `start_index` | [Description] |
| pagination | `end_index` | [Description] |
| pagination | `to_dict` | [Description] |
| pagination | `to_dict` | [Description] |
| rate_limit_middleware | `RateLimitRule` | A rate limiting rule. |
| rate_limit_middleware | `RateLimitEntry` | Tracks request timestamps for rate limiting. |
| rate_limit_middleware | `SlidingWindowRateLimiter` | Sliding window rate limiter for API requests. |
| rate_limit_middleware | `RateLimitMiddleware` | ASGI middleware for rate limiting. |
| rate_limit_middleware | `matches` | Check if this rule matches the request. |
| rate_limit_middleware | `cleanup` | Remove expired timestamps. |
| rate_limit_middleware | `can_request` | Check if a request is allowed. |
| rate_limit_middleware | `record_request` | Record a new request timestamp. |
| rate_limit_middleware | `is_allowed` | Check if a request is allowed under rate limits.

 |
| rate_limit_middleware | `get_status` | Get rate limit status for an identifier. |
| rate_limit_middleware | `reset` | Reset rate limits.

Args:
    identifier: Specific |
| rate_limit_middleware | `add_headers` | [Description] |
| routes | `register_routes` | Register all API routes on the FastAPI app.

Args: |
| routes | `health_check` | Health check endpoint. |
| routes | `search` | Search indexed pages. |
| routes | `list_pages` | List indexed pages. |
| routes | `get_page` | Get a specific page by ID. |
| routes | `get_stats` | Get indexing statistics. |
| routes | `list_interests` | List configured interests. |
| server | `lifespan` | Application lifespan handler for startup/shutdown  |
| server | `create_app` | Create and configure the FastAPI application.

Arg |
| engine | `FilterResult` | Result of content filtering. |
| engine | `ContentFilter` | Filters content based on user interests. |
| engine | `filter_url` | Filter a URL against interest patterns. |
| engine | `filter_content` | Filter content against interest keywords. |
| engine | `filter_page` | Filter a page (Page object or URL string) against  |
| engine | `update_page` | Update a page object with filter results. |
| engine | `should_crawl` | Check if URL should be crawled based on patterns. |
| engine | `extract_relevant_text` | Extract relevant text, truncating if needed. |
| matcher | `ContentMatcher` | Matches content against a single interest. |
| matcher | `InterestFilter` | Filters content against multiple interests. |
| matcher | `matches_content` | Check if content matches this interest's keywords. |
| matcher | `matches_url` | Check if URL matches this interest's patterns. |
| matcher | `relevance_score` | Calculate relevance score for content. |
| matcher | `matches` | Find the best matching interest (highest score). |
| matcher | `get_matching_interests` | Get all matching interests sorted by score. |
| matcher | `should_index` | Check if content should be indexed. |
| matcher | `filter_content` | Filter content and return details if matched. |
| link | `LinkType` | Type of relationship between content items. |
| link | `Link` | Represents a relationship between two content item |
| link | `to_dict` | [Description] |
| link | `from_dict` | [Description] |
| linker | `ContentLinker` | Finds and manages relationships between saved cont |
| linker | `add_item` | Add a content item to the linker. |
| linker | `get_item` | Get a content item by ID. |
| linker | `get_all_items` | Get all stored items. |
| linker | `remove_item` | Remove a content item. |
| linker | `find_related` | Find items related to the given item. |
| linker | `get_all_links` | Get all links for an item as Link objects. |
| linker | `clear_cache` | Clear all cached data. |
| similarity | `SimilarityEngine` | Computes similarity between text items using token |
| similarity | `similarity` | Compute similarity score between two texts (0.0 to |
| similarity | `find_similar` | Find items similar to the query text. |
| timeline | `Timeline` | Manages chronological timeline of content events. |
| timeline | `add_event` | Add an event to the timeline. |
| timeline | `filter_by_type` | Filter entries by event type. |
| timeline | `filter_by_date_range` | Filter entries within a date range. |
| timeline | `filter_by_item_id` | Filter entries by item ID. |
| timeline | `get_events_for_day` | Get all events for a specific day. |
| timeline | `get_events_for_week` | Get all events for a week starting from the given  |
| timeline | `get_events_for_month` | Get all events for a specific month. |
| timeline | `clear` | Clear all timeline entries. |
| timeline | `get_summary` | Get a summary of timeline events. |
| timeline | `to_dict` | Serialize timeline to dict. |
| timeline_entry | `TimelineEventType` | Type of timeline event. |
| timeline_entry | `TimelineEntry` | Represents an event in the content timeline. |
| timeline_entry | `to_dict` | [Description] |
| timeline_entry | `from_dict` | [Description] |
| timeline_view | `ViewMode` | View mode for timeline display. |
| timeline_view | `ViewResult` | Result of rendering a timeline view. |
| timeline_view | `TimelineView` | Renders timeline views in different modes. |
| timeline_view | `to_dict` | [Description] |
| timeline_view | `set_mode` | Set the view mode. |
| timeline_view | `render` | Render the timeline view. |
