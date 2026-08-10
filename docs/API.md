# API Reference

| Module | Export | Description |
|--------|--------|-------------|
| analytics | `AnalyticsData` | Aggregated analytics data. |
| analytics | `AnalyticsTracker` | Track and analyze personal index usage. |
| analytics | `CrawlEvent` | A crawl event record. |
| analytics | `SearchEvent` | A search event record. |
| analytics | `clear` | Clear all tracked events. |
| analytics | `get_analytics` | Compute aggregated analytics. |
| analytics | `get_crawl_events` | Get crawl events, optionally limited. |
| analytics | `get_crawl_stats` | Get detailed crawl statistics. |
| analytics | `get_search_events` | Get search events, optionally limited. |
| analytics | `get_search_stats` | Get detailed search statistics. |
| analytics | `load` | Load analytics data from JSON file. Returns total events loaded. |
| analytics | `record_crawl` | Record a crawl event. |
| analytics | `record_search` | Record a search event. |
| analytics | `save` | Save analytics data to JSON file. |
| annotation | `Annotation` | A single annotation on content. |
| annotation | `AnnotationStore` | Stores and manages annotations. |
| annotation | `AnnotationType` | Types of annotations that can be applied to content. |
| annotation | `add` | Add an annotation to the store.

Args:
    annotation: The annotation to add. |
| annotation | `count` | Total number of annotations in the store. |
| annotation | `get` | Get an annotation by its ID.

Args:
    annotation_id: The ID of the annotati... |
| annotation | `get_by_type` | Get all annotations of a given type.

Args:
    annotation_type: The type to ... |
| annotation | `get_by_url` | Get all annotations for a given URL.

Args:
    url: The URL to look up.

Ret... |
| annotation | `get_stats` | Get statistics about the annotation store.

Returns:
    Dictionary with tota... |
| annotation | `remove` | Remove an annotation by ID.

Args:
    annotation_id: The ID of the annotatio... |
| annotation | `remove_by_url` | Remove all annotations for a given URL.

Args:
    url: The URL whose annotat... |
| annotation | `search` | Search annotations by URL or value. |
| annotation | `to_dict` | Serialize the annotation to a dictionary.

Returns:
    Dictionary representa... |
| annotation | `update` | Update the annotation value and/or metadata.

Args:
    value: New value for ... |
| backup | `BackupManager` | Manage backups of personal index data. |
| backup | `BackupManifest` | Manifest describing a backup. |
| backup | `cleanup_old_backups` | Keep only the N most recent backups. Returns deleted backup IDs. |
| backup | `create_backup` | Create a backup of the source directory. |
| backup | `delete_backup` | Delete a backup and its archive. |
| backup | `from_dict` | Create from dictionary. |
| backup | `get_backup_info` | Get info about a specific backup. |
| backup | `get_total_backup_size` | Get total size of all backups. |
| backup | `list_backups` | List all available backups. |
| backup | `restore_backup` | Restore a backup to the target directory. |
| backup | `to_dict` | Convert to dictionary. |
| bookmark_export | `BookmarkExportResult` | Result of a bookmark export operation. |
| bookmark_export | `BookmarkExporter` | Export bookmarks to HTML, JSON, and OPML formats.

Accepts a list of Bookmark... |
| bookmark_export | `export` | Export bookmarks in the specified format.

Args:
    fmt: One of 'json', 'htm... |
| bookmark_export | `export_html` | Export bookmarks as Netscape HTML bookmark format.

Produces a standard Netsc... |
| bookmark_export | `export_json` | Export bookmarks as a pretty-printed JSON string.

Returns a JSON array where... |
| bookmark_export | `export_opml` | Export bookmarks as OPML 2.0 format.

Produces a valid OPML 2.0 document with... |
| bookmark_export | `export_to_file` | Export bookmarks to a file.

Args:
    filepath: Destination file path. Forma... |
| bookmarks | `Bookmark` | A single bookmark entry. |
| bookmarks | `BookmarkManager` | Manage bookmarks for the personal index. |
| bookmarks | `add` | Add a bookmark, updating if URL already exists. |
| bookmarks | `count` | Count total bookmarks. |
| bookmarks | `from_dict` | Create from dictionary. |
| bookmarks | `get` | Get a bookmark by URL. |
| bookmarks | `get_all_tags` | Get all unique tags. |
| bookmarks | `get_categories` | Get all unique categories. |
| bookmarks | `list_all` | List all bookmarks. |
| bookmarks | `list_by_category` | List bookmarks in a category. |
| bookmarks | `list_by_tag` | List bookmarks with a specific tag. |
| bookmarks | `list_favorites` | List favorite bookmarks. |
| bookmarks | `load` | Load bookmarks from JSON file. Returns count loaded. |
| bookmarks | `remove` | Remove a bookmark by URL. Returns True if removed. |
| bookmarks | `save` | Save bookmarks to JSON file. |
| bookmarks | `search` | Search bookmarks by title, description, or URL. |
| bookmarks | `to_dict` | Convert to dictionary. |
| bookmarks | `toggle_favorite` | Toggle favorite status of a bookmark. |
| cache | `CacheDecorator` | Decorator that wraps a function with caching.

Usage:
    @CacheDecorator(lru... |
| cache | `LRUCache` | Thread-safe LRU cache with optional size limit.

Uses OrderedDict for O(1) ge... |
| cache | `TTLCache` | Cache with time-to-live expiration.

Each entry expires after the specified T... |
| cache | `clear` | Remove all items from cache. |
| cache | `delete` | Remove key from cache.

Args:
    key: Cache key to remove.

Returns:
    Tru... |
| cache | `get` | Get value by key, moving it to end (most recently used).

Args:
    key: Cach... |
| cache | `hit_rate` | Cache hit rate as a fraction (0.0 to 1.0). |
| cache | `put` | Store value in cache, evicting LRU item if at capacity.

Args:
    key: Cache... |
| cache | `size` | Current number of items in cache. |
| cache | `stats` | Return cache statistics. |
| cache | `wrapper` | [No description] |
| cli | `add_interest` | Add a new interest to track. |
| cli | `add_schedule` | Add a scheduled crawl job. |
| cli | `config` | Manage configuration. |
| cli | `config_set_crawler` | Set crawler configuration. |
| cli | `config_set_schedule` | Set schedule configuration. |
| cli | `config_show` | Show current configuration. |
| cli | `crawl` | Crawl a URL and index matching content. |
| cli | `get_config_manager` | Get the config manager instance. |
| cli | `index` | Manage the search index. |
| cli | `index_clear` | Clear the search index. |
| cli | `index_count` | Show number of indexed pages. |
| cli | `index_list` | List indexed pages. |
| cli | `interests` | Manage tracked interests. |
| cli | `list_interests` | List all tracked interests. |
| cli | `list_schedule` | List scheduled jobs. |
| cli | `main` | personal-index - Track and index content matching your interests. |
| cli | `remove_interest` | Remove an interest by name. |
| cli | `remove_schedule` | Remove a scheduled job. |
| cli | `save` | [No description] |
| cli | `schedule` | Manage scheduled crawling jobs. |
| cli | `search` | Search indexed pages. |
| cli | `toggle_interest` | Toggle an interest on/off. |
| content | `ExtractedContent` | Content extracted from a web page. |
| content | `compute_tf` | Compute term frequency for a list of tokens. |
| content | `extract_content` | Extract structured content from HTML. |
| content | `get_keywords` | Extract keywords from meta keywords and headings. |
| content | `get_searchable_text` | Get combined searchable text from title, headings, and body. |
| content | `remove_stopwords` | Remove stopwords from token list. |
| content | `tokenize` | Tokenize text into lowercase words. |
| content_annotations | `Annotation` | A user annotation on a saved content item. |
| content_annotations | `AnnotationManager` | Manages user annotations on saved content items. |
| content_annotations | `AnnotationType` | Types of annotations users can add to content. |
| content_annotations | `add` | Add an annotation. |
| content_annotations | `add_tag` | Add a tag to this annotation. |
| content_annotations | `clear` | Remove all annotations. |
| content_annotations | `count` | Return total number of annotations. |
| content_annotations | `delete` | Delete an annotation. |
| content_annotations | `delete_by_content_id` | Delete all annotations for a content item. Returns count deleted. |
| content_annotations | `deserialize` | Deserialize annotations from a list of dicts. |
| content_annotations | `from_dict` | Deserialize from dictionary. |
| content_annotations | `get` | Get an annotation by ID. |
| content_annotations | `get_all` | Get all annotations. |
| content_annotations | `get_by_author` | Get all annotations by a specific author. |
| content_annotations | `get_by_content_id` | Get all annotations for a content item. |
| content_annotations | `get_by_tag` | Get all annotations with a specific tag. |
| content_annotations | `get_by_type` | Get all annotations of a specific type. |
| content_annotations | `get_recent` | Get the most recent annotations. |
| content_annotations | `get_stats` | Get annotation statistics. |
| content_annotations | `remove_tag` | Remove a tag from this annotation. |
| content_annotations | `search` | Search annotations by text content. |
| content_annotations | `serialize` | Serialize all annotations to a list of dicts. |
| content_annotations | `to_dict` | Serialize to dictionary. |
| content_annotations | `update_text` | Update the annotation text. |
| content_categorizer | `CategorizationResult` | Result of content categorization. |
| content_categorizer | `ContentCategorizer` | Classifies content into topic categories using multi-signal analysis.

Signal... |
| content_categorizer | `TopicCategory` | A topic category with associated keywords and metadata. |
| content_categorizer | `TopicScore` | Score for a single topic assignment. |
| content_categorizer | `add_topic` | Add or update a topic category.

Args:
    name: Topic name (lowercase, no sp... |
| content_categorizer | `categorize` | Categorize content into topics.

Args:
    text: Main content text to analyze... |
| content_categorizer | `categorize_batch` | Categorize multiple content items.

Args:
    items: List of dicts with keys ... |
| content_categorizer | `get_topic` | Get a topic category by name. |
| content_categorizer | `get_topics` | Get list of all available topic names. |
| content_categorizer | `remove_topic` | Remove a topic category.

Args:
    name: Topic name to remove.

Returns:
   ... |
| content_categorizer | `secondary_topics` | Return topics after the primary one. |
| content_categorizer | `top_n` | Return top N topics. |
| content_collections | `Collection` | A collection of saved content items. |
| content_collections | `CollectionManager` | Manages collections of saved content items. |
| content_collections | `add_item` | Add an item to this collection. |
| content_collections | `add_items` | Add multiple items to a collection. |
| content_collections | `clear_items` | Remove all items from a collection. |
| content_collections | `contains` | Check if an item is in this collection. |
| content_collections | `count` | Return total number of collections. |
| content_collections | `create` | Create a new collection. Returns the collection ID. |
| content_collections | `delete` | Delete a collection. |
| content_collections | `deserialize` | Deserialize collections from a list of dicts. |
| content_collections | `from_dict` | Deserialize from dictionary. |
| content_collections | `get` | Get a collection by ID. |
| content_collections | `get_collections_for_item` | Get all collections containing a specific item. |
| content_collections | `get_items` | Get all item IDs in a collection. |
| content_collections | `get_recent` | Get the most recently created collections. |
| content_collections | `get_stats` | Get collection statistics. |
| content_collections | `item_count` | Return the number of items in this collection. |
| content_collections | `list_all` | List all collections. |
| content_collections | `list_private` | List all private collections. |
| content_collections | `list_public` | List all public collections. |
| content_collections | `merge` | Merge source collection into target collection, deleting source. |
| content_collections | `move_item` | Move an item from one collection to another. |
| content_collections | `remove_item` | Remove an item from this collection. |
| content_collections | `rename` | Rename a collection (alias for update_name). |
| content_collections | `search` | Search collections by name or description. |
| content_collections | `serialize` | Serialize all collections to a list of dicts. |
| content_collections | `to_dict` | Serialize to dictionary. |
| content_collections | `toggle_public` | Toggle the public/private status of a collection. |
| content_collections | `update_description` | Update the description of a collection. |
| content_collections | `update_name` | Update the name of a collection. |
| content_dedup | `AddItemResult` | Result of adding an item to the deduplicator. |
| content_dedup | `BatchDedupReport` | Generate a report of deduplication results. |
| content_dedup | `ContentDeduplicator` | Detect duplicate or near-duplicate saved content.

Supports hash-based exact ... |
| content_dedup | `DedupConfig` | Configuration for content deduplication. |
| content_dedup | `DedupResult` | Result of deduplication analysis. |
| content_dedup | `DuplicateGroup` | A group of duplicate content items. |
| content_dedup | `SimilarityMethod` | Available similarity detection methods. |
| content_dedup | `add_items` | Add items incrementally and check for duplicates.

Args:
    items: List of c... |
| content_dedup | `clear` | Clear all stored state. |
| content_dedup | `duplicate_ratio` | Ratio of duplicate items to total items. |
| content_dedup | `find_duplicates` | Find duplicate groups among content items.

Args:
    items: List of dicts wi... |
| content_dedup | `get_unique_items` | Get unique items, removing duplicates.

Args:
    items: List of content item... |
| content_dedup | `to_dict` | Convert report to dictionary. |
| content_dedup | `to_summary_string` | Generate a human-readable summary. |
| content_dedup | `total_count` | Total items in this group (representative + duplicates). |
| content_enricher | `ContentEnricher` | Enrich content with computed metadata and analysis. |
| content_enricher | `EnrichedContent` | Content with enriched metadata. |
| content_enricher | `batch_enrich` | Enrich multiple content items.

Args:
    items: List of (title, text) tuples... |
| content_enricher | `enrich` | Enrich content with computed metadata.

Args:
    title: Content title.
    t... |
| content_enricher | `to_dict` | Convert to dictionary representation. |
| content_export_csv | `CSVExporter` | Exports content items as CSV and other formats. |
| content_export_csv | `ExportFormat` | Supported export formats. |
| content_export_csv | `ExportStats` | Statistics about an export operation. |
| content_export_csv | `export` | Export items to the specified format. |
| content_export_csv | `export_to_file` | Export items to a file. |
| content_export_csv | `get_stats` | Get export statistics. |
| content_extractor | `ContentExtractor` | Extracts meaningful content from HTML pages. |
| content_extractor | `ExtractedContent` | Content extracted from an HTML page. |
| content_extractor | `extract` | Extract content from HTML string. |
| content_extractor | `extract_readability_score` | Calculate a readability score for extracted content. |
| content_favicon | `FaviconConfig` | Configuration for favicon extraction. |
| content_favicon | `FaviconExtractor` | Extract favicons from URLs and HTML content. |
| content_favicon | `FaviconFormat` | Format of the favicon. |
| content_favicon | `FaviconHTMLParser` | Parse HTML to extract favicon links. |
| content_favicon | `FaviconInfo` | Information about a favicon. |
| content_favicon | `FaviconManager` | Manage favicon extraction and caching. |
| content_favicon | `FaviconResult` | Result of favicon extraction. |
| content_favicon | `FaviconSource` | Source of the favicon. |
| content_favicon | `FaviconStatus` | Status of favicon extraction. |
| content_favicon | `FaviconStore` | Store and retrieve favicon results. |
| content_favicon | `all_domains` | Get all domains with stored favicons. |
| content_favicon | `batch_extract` | Extract favicons for multiple URLs. |
| content_favicon | `clear` | Clear all stored favicons. |
| content_favicon | `clear_cache` | Clear the favicon cache. Returns number of entries cleared. |
| content_favicon | `contains` | Check if a domain has a stored favicon. |
| content_favicon | `count` | Get the number of stored favicons. |
| content_favicon | `extension` | Get the file extension. |
| content_favicon | `extract_domain` | Extract domain from a URL. |
| content_favicon | `extract_favicon` | Extract favicon for a URL. |
| content_favicon | `extract_from_html` | Extract favicon information from HTML content. |
| content_favicon | `from_dict` | Deserialize from dictionary. |
| content_favicon | `get` | Get a favicon result for a domain. |
| content_favicon | `get_cached` | Get a cached favicon result. |
| content_favicon | `get_favicon_url` | Get the default favicon URL for a given URL. |
| content_favicon | `get_google_favicon_url` | Get favicon URL via Google's favicon service. |
| content_favicon | `get_summary` | Get a summary of favicon extraction. |
| content_favicon | `handle_starttag` | Handle start tags to find favicon links. |
| content_favicon | `is_failed` | Check if the extraction failed. |
| content_favicon | `is_ready` | Check if the favicon is ready. |
| content_favicon | `mime_type` | Get the MIME type. |
| content_favicon | `refresh_favicon` | Refresh a favicon by re-extracting. |
| content_favicon | `remove` | Remove a favicon result. Returns True if removed. |
| content_favicon | `store` | Store a favicon result for a domain. |
| content_favicon | `to_dict` | Serialize to dictionary. |
| content_feed | `FeedFormat` | Supported feed formats. |
| content_feed | `FeedGenerator` | Generates RSS and Atom feeds. |
| content_feed | `FeedItem` | A single item in a feed. |
| content_feed | `add_item` | Add an item to the feed. |
| content_feed | `add_items` | Add multiple items to the feed. |
| content_feed | `clear` | Remove all items from the feed. |
| content_feed | `from_dict` | Deserialize from dictionary. |
| content_feed | `generate` | Generate feed content in the specified format. |
| content_feed | `get_feed_type` | Get the MIME type for a feed format. |
| content_feed | `to_dict` | Serialize to dictionary. |
| content_filter | `ContentFilter` | Filters crawled pages based on interests and configuration. |
| content_filter | `FilterConfig` | Configuration for content filtering. |
| content_filter | `filter_pages` | Filter a list of pages, returning only included ones. |
| content_filter | `get_filter_reasons` | Get list of reasons why a page was filtered out. |
| content_filter | `should_include` | Determine if a page should be included in the index. |
| content_health | `UrlHealthResult` | Result of URL health check.

Attributes:
    url: The checked URL.
    status... |
| content_health | `check_content_urls` | Check accessibility of multiple content URLs.

Args:
    urls: List of URLs t... |
| content_health | `check_health` | Check overall content health status.

Args:
    data_dir: Path to data direct... |
| content_health | `check_url_accessibility` | Check if a URL is accessible.

Args:
    url: URL to check.
    timeout: Requ... |
| content_health | `to_dict` | Serialize to a plain dict. |
| content_import_html | `HTMLBookmark` | A bookmark imported from Netscape HTML format. |
| content_import_html | `HTMLImportResult` | Result of an HTML bookmark import operation. |
| content_import_html | `HTMLImporter` | Import bookmarks from Netscape HTML bookmark format. |
| content_import_html | `from_dict` | Process from_dict.

Args:
data. |
| content_import_html | `import_html` | Import bookmarks from Netscape HTML content string. |
| content_import_html | `is_success` | Is_success. |
| content_import_html | `to_dict` | Serialize to a dictionary.

Returns:
    Dictionary representation. |
| content_scheduler | `ContentScheduler` | Schedule and manage periodic content re-indexing tasks. |
| content_scheduler | `ScheduleFrequency` | How often to run a scheduled task. |
| content_scheduler | `ScheduledTask` | A task to be run on a schedule. |
| content_scheduler | `TaskResult` | Result of running a scheduled task. |
| content_scheduler | `add_task` | Add a new scheduled task. |
| content_scheduler | `clear_results` | Clear all task results. |
| content_scheduler | `disable_task` | Disable a task. |
| content_scheduler | `enable_task` | Enable a task. |
| content_scheduler | `get_due_tasks` | Get all tasks that are due. |
| content_scheduler | `get_enabled_tasks` | Get all enabled tasks. |
| content_scheduler | `get_recent_results` | Get the most recent task results. |
| content_scheduler | `get_task` | Get a task by name. |
| content_scheduler | `get_task_stats` | Get statistics about all tasks. |
| content_scheduler | `get_tasks_by_tag` | Get tasks with a specific tag. |
| content_scheduler | `interval_seconds` | Return the interval in seconds for this frequency. |
| content_scheduler | `is_due` | Check if the task is due to run. |
| content_scheduler | `mark_error` | Record an error from the task. |
| content_scheduler | `mark_run` | Mark the task as having run. |
| content_scheduler | `remove_task` | Remove a scheduled task by name. |
| content_scheduler | `reset_task` | Reset a task's run state. |
| content_scheduler | `results` | Return a copy of all task results. |
| content_scheduler | `run_due_tasks` | Run all tasks that are due. |
| content_scheduler | `run_task` | Run a specific task immediately. |
| content_scheduler | `start` | Start the scheduler in a background thread. |
| content_scheduler | `stop` | Stop the scheduler. |
| content_scheduler | `tasks` | Return a copy of all scheduled tasks. |
| content_scoring | `ContentScorer` | Multi-factor content quality scorer.

Evaluates content based on length, keyw... |
| content_scoring | `ScoreBreakdown` | Detailed breakdown of content quality scores. |
| content_scoring | `rank` | Rank a list of content items by score (highest first).

Args:
    items: List... |
| content_scoring | `score` | Score a content item based on multiple factors.

Args:
    content: Dict with... |
| content_search_fulltext | `BM25Ranker` | BM25 ranking algorithm for document scoring. |
| content_search_fulltext | `SearchIndex` | Full-text search index with BM25 ranking. |
| content_search_fulltext | `SearchQuery` | A search query with optional filters. |
| content_search_fulltext | `SearchResult` | A single search result. |
| content_search_fulltext | `SearchResults` | Collection of search results with metadata. |
| content_search_fulltext | `Tokenizer` | Tokenizes text into searchable terms. |
| content_search_fulltext | `add_document` | Add or update a document in the index. |
| content_search_fulltext | `clear` | Clear the entire index. |
| content_search_fulltext | `compute_score` | Compute BM25 score for a document given query tokens. |
| content_search_fulltext | `deserialize` | Deserialize the index. |
| content_search_fulltext | `doc_count` | Return the number of indexed documents. |
| content_search_fulltext | `from_dict` | Deserialize from dictionary. |
| content_search_fulltext | `get_all_ids` | Get all document IDs. |
| content_search_fulltext | `get_document` | Get a document by ID. |
| content_search_fulltext | `get_stats` | Get index statistics. |
| content_search_fulltext | `remove_document` | Remove a document from the index. |
| content_search_fulltext | `search` | Search the index and return ranked results. |
| content_search_fulltext | `search_query` | Search using a SearchQuery object. |
| content_search_fulltext | `serialize` | Serialize the index. |
| content_search_fulltext | `to_dict` | Serialize to dictionary. |
| content_search_fulltext | `tokenize` | Tokenize text into lowercase words, removing stopwords. |
| content_search_fulltext | `update_document` | Update an existing document. |
| content_social_preview | `PreviewCardConfig` | Configuration for preview card generation. |
| content_social_preview | `PreviewCardGenerator` | Generate SVG preview cards. |
| content_social_preview | `PreviewCardManager` | Manage preview card generation and storage. |
| content_social_preview | `PreviewCardResult` | Result of preview card generation. |
| content_social_preview | `PreviewCardSize` | Size configuration for preview cards. |
| content_social_preview | `PreviewCardStyle` | Visual style for preview cards. |
| content_social_preview | `PreviewCardTemplate` | Template for preview card generation. |
| content_social_preview | `PreviewCardType` | Type of preview card. |
| content_social_preview | `SocialPlatform` | Social platform configuration. |
| content_social_preview | `SocialPreviewConfig` | Configuration for social preview generation. |
| content_social_preview | `SocialPreviewEngine` | High-level engine for social preview generation. |
| content_social_preview | `SocialPreviewResult` | Result of social preview generation. |
| content_social_preview | `SocialPreviewStatus` | Status of social preview generation. |
| content_social_preview | `aspect_ratio` | Calculate the aspect ratio. |
| content_social_preview | `clear_cache` | Clear the cache. |
| content_social_preview | `create_card` | Create a preview card. |
| content_social_preview | `create_card_batch` | Create cards for multiple items. |
| content_social_preview | `from_dict` | Deserialize from dictionary. |
| content_social_preview | `generate_card` | Generate an SVG preview card. |
| content_social_preview | `generate_card_batch` | Generate card SVGs for multiple items. |
| content_social_preview | `generate_preview` | Generate a social preview for a URL. |
| content_social_preview | `get_cached` | Get a cached card result. |
| content_social_preview | `get_card` | Get a card by URL. |
| content_social_preview | `get_summary` | Get a summary of cards. |
| content_social_preview | `get_template` | Get a template by style name. |
| content_social_preview | `is_failed` | Check if generation failed. |
| content_social_preview | `is_ready` | Check if the card is ready. |
| content_social_preview | `to_dict` | Serialize to dictionary. |
| content_summarizer | `ArticleSummarizer` | High-level API for summarizing articles with metadata. |
| content_summarizer | `ContentSummarizer` | Extract key points from saved articles using extractive summarization. |
| content_summarizer | `KeyPoint` | A key point extracted from content. |
| content_summarizer | `SummaryConfig` | Configuration for summarization. |
| content_summarizer | `SummaryResult` | Result of content summarization. |
| content_summarizer | `batch_summarize` | Summarize multiple texts.

Args:
    texts: List of article texts.

Returns:
... |
| content_summarizer | `summarize` | Generate a summary with key points from the text.

Args:
    text: The articl... |
| content_summarizer | `summarize_article` | Summarize an article with full metadata.

Args:
    title: Article title.
   ... |
| content_summarizer | `summarize_articles` | Summarize multiple articles.

Args:
    articles: List of article dicts with ... |
| content_thumbnail | `ThumbnailConfig` | Configuration for thumbnail generation. |
| content_thumbnail | `ThumbnailEngine` | High-level engine for thumbnail operations. |
| content_thumbnail | `ThumbnailFormat` | Image format for thumbnails. |
| content_thumbnail | `ThumbnailGenerator` | Generates thumbnail images for saved content. |
| content_thumbnail | `ThumbnailMetadata` | Metadata about a generated thumbnail. |
| content_thumbnail | `ThumbnailProcessor` | Processes and manages thumbnail generation for multiple items. |
| content_thumbnail | `ThumbnailResult` | Result of thumbnail generation. |
| content_thumbnail | `ThumbnailSize` | Thumbnail size configuration. |
| content_thumbnail | `ThumbnailStatus` | Status of thumbnail generation. |
| content_thumbnail | `ThumbnailStyle` | Visual style for thumbnails. |
| content_thumbnail | `area` | Calculate the area of the thumbnail. |
| content_thumbnail | `clear_cache` | Clear the thumbnail cache. Returns number of entries cleared. |
| content_thumbnail | `extension` | Get the file extension for this format. |
| content_thumbnail | `from_dict` | Deserialize from dictionary. |
| content_thumbnail | `generate` | Generate a thumbnail for a URL. |
| content_thumbnail | `generate_batch` | Generate thumbnails for multiple items. |
| content_thumbnail | `generate_svg_thumbnail` | Generate an SVG thumbnail. |
| content_thumbnail | `generate_thumbnail` | Generate a thumbnail for a URL. |
| content_thumbnail | `get_all_metadata` | Get all metadata. |
| content_thumbnail | `get_all_results` | Get all results. |
| content_thumbnail | `get_cached` | Get a cached thumbnail result. |
| content_thumbnail | `get_failed_count` | Count failed thumbnails. |
| content_thumbnail | `get_metadata` | Get metadata for a URL. |
| content_thumbnail | `get_ready_count` | Count ready thumbnails. |
| content_thumbnail | `get_result` | Get a result by thumbnail ID. |
| content_thumbnail | `get_summary` | Get a summary of processing. |
| content_thumbnail | `get_svg` | Get SVG thumbnail content directly. |
| content_thumbnail | `is_expired` | Check if the thumbnail metadata has expired. |
| content_thumbnail | `is_failed` | Check if the thumbnail generation failed. |
| content_thumbnail | `is_ready` | Check if the thumbnail is ready. |
| content_thumbnail | `mime_type` | Get the MIME type for this format. |
| content_thumbnail | `process_batch` | Process a batch of items. Each item is a dict with url, title, domain keys. |
| content_thumbnail | `process_url` | Process a single URL and generate its thumbnail. |
| content_thumbnail | `to_dict` | Serialize to dictionary. |
| content_type | `ContentTypeDetector` | Detects and classifies content types from URLs, filenames, or raw data. |
| content_type | `ContentTypeInfo` | Information about detected content type. |
| content_type | `classify` | Classify a MIME type into a category.

Args:
    content_type: MIME type stri... |
| content_type | `detect_from_bytes` | Detect content type from raw bytes (magic number detection).

Args:
    data:... |
| content_type | `detect_from_extension` | Detect content type from a file extension.

Args:
    ext: File extension (wi... |
| content_type | `detect_from_filename` | Detect content type from a filename.

Args:
    filename: The filename to ana... |
| content_type | `detect_from_url` | Detect content type from a URL.

Args:
    url: The URL to analyze.

Returns:... |
| content_type | `is_downloadable` | Whether this content type should be downloaded. |
| content_type | `should_index` | Determine if content at URL should be indexed.

Args:
    url: The URL to che... |
| crawl_stats | `CrawlStats` | Tracks crawl statistics across all domains. |
| crawl_stats | `DomainStats` | Statistics for a single domain. |
| crawl_stats | `domain_count` | Number of unique domains tracked. |
| crawl_stats | `error_count` | Number of errors recorded. |
| crawl_stats | `get_domain_stats` | Get or create stats for a domain.

Args:
    domain: The domain name.

Return... |
| crawl_stats | `get_domain_summaries` | Get per-domain summaries.

Returns:
    List of domain stat dictionaries. |
| crawl_stats | `get_summary` | Get an overall summary of crawl statistics.

Returns:
    Dictionary with agg... |
| crawl_stats | `record_failure` | Record a failed URL crawl.

Args:
    error: Error message.
    status_code: ... |
| crawl_stats | `record_skip` | Record a skipped URL. |
| crawl_stats | `record_success` | Record a successful URL crawl.

Args:
    bytes_downloaded: Number of bytes d... |
| crawl_stats | `record_url_crawled` | Record a successfully crawled URL.

Args:
    domain: The domain of the URL.
... |
| crawl_stats | `record_url_failed` | Record a failed URL crawl.

Args:
    domain: The domain of the URL.
    erro... |
| crawl_stats | `record_url_skipped` | Record a skipped URL.

Args:
    domain: The domain of the URL. |
| crawl_stats | `reset` | Reset all crawl statistics. |
| crawl_stats | `success_rate` | Ratio of successful URLs to total attempted. |
| crawl_stats | `to_dict` | Serialize domain stats to a dictionary.

Returns:
    Dictionary representati... |
| crawl_stats | `total_bytes` | Total bytes downloaded across all URLs. |
| crawl_stats | `total_requests` | Total number of requests (crawled + failed + skipped). |
| crawl_stats | `total_urls` | Total number of URLs processed. |
| crawl_stats | `uptime` | Seconds since crawl tracking started. |
| dedup | `DeduplicationEngine` | Detect duplicate or near-duplicate content. |
| dedup | `DocumentHash` | Hash representation of a document. |
| dedup | `clear` | Clear all stored hashes. |
| dedup | `compute_fingerprint` | Compute a shorter fingerprint for quick comparison. |
| dedup | `compute_hash` | Compute SHA-256 hash of text. |
| dedup | `document_count` | Number of unique documents stored. |
| dedup | `duplicate_count` | Number of duplicates detected. |
| dedup | `from_text` | Create a DocumentHash from page data. |
| dedup | `get_original_url` | Get the original URL for a duplicate. |
| dedup | `is_duplicate` | Check if content is a duplicate. Returns (is_dup, original_url). |
| dedup | `is_near_duplicate` | Check for near-duplicates using token overlap. Returns (is_dup, url, score). |
| domains | `DomainManager` | Manages domain allow/block rules. |
| domains | `DomainRule` | Rule for a specific domain. |
| domains | `add_allow` | Add an allow rule for a domain.

Args:
    domain: The domain to allow.
    m... |
| domains | `add_block` | Add a block rule for a domain.

Args:
    domain: The domain to block.
    re... |
| domains | `from_dict` | Create a DomainRule from a dictionary.

Args:
    data: Dictionary with rule ... |
| domains | `get_max_depth` | Get the maximum crawl depth for a domain.

Args:
    domain: The domain to ch... |
| domains | `get_page_count` | Get the number of pages crawled from a domain.

Args:
    domain: The domain ... |
| domains | `is_allowed` | Check if a domain is allowed for crawling.

Args:
    domain: The domain to c... |
| domains | `is_blocked` | Check if a domain is explicitly blocked.

Args:
    domain: The domain to che... |
| domains | `list_rules` | List all domain rules.

Returns:
    List of all DomainRule objects. |
| domains | `record_page` | Record that a page was crawled from a domain. |
| domains | `remove` | Remove a domain rule.

Args:
    domain: The domain whose rule to remove.

Re... |
| domains | `reset_counts` | Reset all page counts. |
| domains | `to_dict` | Serialize the domain rule to a dictionary.

Returns:
    Dictionary represent... |
| encoding | `EncodingDetector` | Detects text encoding and performs conversions. |
| encoding | `EncodingResult` | Result of encoding detection. |
| encoding | `convert` | Convert between encodings. |
| encoding | `decode` | Decode bytes to string, auto-detecting if needed. |
| encoding | `detect` | Detect the encoding of byte data. |
| encoding | `encode` | Encode string to bytes. |
| encoding | `normalize_whitespace` | Normalize whitespace in text. |
| encoding | `remove_control_chars` | Remove control characters from text. |
| encoding | `sanitize` | Sanitize text by removing control chars and normalizing whitespace. |
| export | `ExportResult` | Result of an export operation. |
| export | `Exporter` | Export bookmarks to various file formats. |
| export | `export_filtered` | Export filtered bookmarks to a string. |
| export | `export_to_content` | Export bookmarks to a string in the specified format. |
| export | `export_to_file` | Export bookmarks to a file, auto-detecting format from extension. |
| export | `manager` | Manager. |
| export_markdown | `ExportConfig` | Configuration for content export. |
| export_markdown | `ExportFormat` | Supported export formats. |
| export_markdown | `MarkdownExporter` | Export saved content as markdown, HTML, or plain text.

Supports sorting by d... |
| export_markdown | `export` | Export content items to the specified format.

Args:
    items: List of conte... |
| formatter | `format_crawl_stats` | Format crawl statistics. |
| formatter | `format_duration` | Format duration in seconds to human-readable string. |
| formatter | `format_file_size` | Format file size in bytes to human-readable string. |
| formatter | `format_index_page` | Format an indexed page for display. |
| formatter | `format_interest` | Format an interest for display. |
| formatter | `format_schedule_job` | Format a scheduled job for display. |
| formatter | `format_search_results` | Format search results for display. |
| formatter | `format_table` | Format data as a text table. |
| formatter | `format_timestamp` | Format a timestamp string for display. |
| formatter | `highlight` | Highlight search terms in text with ** markers. |
| formatter | `truncate` | Truncate text to max_length, adding ellipsis. |
| fuzzy_search | `FuzzyMatch` | Result of a fuzzy search match. |
| fuzzy_search | `FuzzySearcher` | Perform fuzzy string matching for search queries. |
| fuzzy_search | `highlight` | Create highlighted version of text with matched indices. |
| fuzzy_search | `highlight_html` | Create HTML-highlighted version of text. |
| fuzzy_search | `search` | Search for query in a list of texts, returning fuzzy matches. |
| fuzzy_search | `search_in_dict` | Search in both keys and values of a dictionary. |
| fuzzy_search | `search_with_highlight` | Search and return matches with highlighted text. |
| health | `HealthCheckResult` | Result of a single health check. |
| health | `HealthChecker` | Run health checks on the personal index system. |
| health | `HealthReport` | Complete health report. |
| health | `check_config_file` | Check configuration file. |
| health | `check_data_directory` | Check data directory exists and is accessible. |
| health | `check_database` | Check SQLite database integrity. |
| health | `check_dependencies` | Check that required dependencies are installed. |
| health | `check_disk_space` | Check available disk space. |
| health | `check_permissions` | Check file permissions on data directory. |
| health | `check_python_version` | Check Python version compatibility. |
| health | `check_storage_integrity` | Check storage file integrity. |
| health | `run_all` | Run all health checks. |
| health | `summary` | Summary. |
| health | `to_dict` | To_dict. |
| health_report | `HealthCheckResult` | Result of a single health check. |
| health_report | `HealthReport` | Complete system health report. |
| health_report | `HealthReporter` | Generates comprehensive health reports for the system. |
| health_report | `generate_report` | Generate a full health report.

Args:
    extra_checks: Optional list of call... |
| health_report | `is_degraded` | True if any check is degraded but none unhealthy. |
| health_report | `is_healthy` | True if all checks are healthy. |
| health_report | `to_dict` | Convert report to dictionary. |
| importer | `ImportResult` | Result of an import operation. |
| importer | `Importer` | Import bookmarks from various file formats. |
| importer | `import_from_content` | Import bookmarks from content string with specified format. |
| importer | `import_from_file` | Import bookmarks from a file, auto-detecting format. |
| importer | `import_opml` | Import from OPML format. |
| importer | `manager` | Manager. |
| index | `IndexedPage` | A page stored in the search index. |
| index | `SearchIndex` | Search index with SQLite-like persistence via JSON. |
| index | `SearchResult` | A result from a search query. |
| index | `add_page` | Add a page to the index. Returns page id. |
| index | `clear` | Clear the index. |
| index | `close` | Close the index (save). |
| index | `from_dict` | Process from_dict.

Args:
data. |
| index | `get_page` | Get a page by URL. |
| index | `get_page_count` | Get number of indexed pages. |
| index | `list_pages` | List all pages sorted by score. |
| index | `remove_page` | Remove a page from the index. |
| index | `search` | Search the index. |
| index | `to_dict` | Serialize the index entry to a dictionary.

Returns:
    Dictionary represent... |
| indexer | `SearchIndex` | Full-text search index with TF-IDF-like scoring. |
| indexer | `add_page` | Add a page to the index. |
| indexer | `clear` | Clear the entire index. |
| indexer | `get_all_pages` | Get all indexed pages. |
| indexer | `get_page` | Get a page by ID. |
| indexer | `load` | Load index from disk. |
| indexer | `num_documents` | Number of documents in the index. |
| indexer | `num_terms` | Number of unique terms in the inverted index. |
| indexer | `remove_page` | Remove a page from the index. |
| indexer | `save` | Save index to disk. |
| indexer | `search` | Search the index for a query. |
| interest_store | `InterestStore` | Persistent storage for user interests. |
| interest_store | `add` | Add an interest to the store. |
| interest_store | `get` | Get an interest by name. |
| interest_store | `list_all` | List all interests, optionally filtering by enabled status. |
| interest_store | `matches_any` | Find all interests that match the given text/url. |
| interest_store | `remove` | Remove an interest by name. Returns True if found and removed. |
| interest_store | `toggle` | Toggle an interest's enabled status. |
| interest_store | `total_score` | Calculate total relevance score across all interests. |
| interest_store | `update_priority` | Update an interest's priority (clamped 1-10). |
| interests | `Interest` | User interest for tracking topics. |
| interests | `InterestStore` | Persistent storage for interests (CLI-facing). |
| interests | `add` | Add an interest. |
| interests | `from_dict` | Deserialize from dictionary. |
| interests | `get` | Get an interest by name. |
| interests | `get_all_keywords` | Get all keywords from all interests (lowercase). |
| interests | `get_all_topics` | Get all topics from all interests (lowercase). |
| interests | `get_all_url_patterns` | Get all compiled URL patterns. |
| interests | `get_enabled` | List enabled interests. |
| interests | `list_all` | List all interests. |
| interests | `remove` | Remove an interest by name. |
| interests | `to_dict` | Serialize to dictionary. |
| interests | `toggle` | Toggle an interest's enabled status. |
| keyword_extractor | `Keyword` | A keyword with its frequency and score. |
| keyword_extractor | `KeywordExtractor` | Extract keywords from text using frequency-based analysis. |
| keyword_extractor | `compare_keywords` | Compare keywords between two texts, returning shared keywords with scores. |
| keyword_extractor | `compute_term_frequency` | Compute term frequency for each token in text. |
| keyword_extractor | `extract` | Extract keywords from text. |
| keyword_extractor | `extract_phrases` | Extract n-gram phrases from text. |
| keyword_extractor | `extract_top_n` | Extract top N keywords as plain strings. |
| link_analyzer | `LinkAnalysisResult` | Result of link analysis. |
| link_analyzer | `LinkAnalyzer` | Analyzes links on crawled pages. |
| link_analyzer | `LinkStats` | Statistics about links on a page. |
| link_analyzer | `analyze` | Analyze links found on a page. |
| link_analyzer | `analyze_batch` | Analyze links across multiple pages. |
| link_analyzer | `get_aggregate_stats` | Get aggregate statistics across multiple analyses. |
| link_preview | `LinkPreview` | Structured preview card for a URL, populated from OG/Twitter meta tags.

Fiel... |
| link_preview | `LinkPreviewGenerator` | Generates LinkPreview cards from HTML content.

Extracts Open Graph and Twitt... |
| link_preview | `generate` | Generate a LinkPreview from HTML content.

Args:
    html: Raw HTML string to... |
| logging_config | `get_logger` | Get a logger for a specific module. |
| logging_config | `setup_logging` | Configure logging for the personal_index package. |
| metrics | `MetricsCollector` | Collects and reports system and application metrics. |
| metrics | `SystemMetrics` | Snapshot of system metrics. |
| metrics | `collect_system_metrics` | Collect current system metrics.

Args:
    target_path: Filesystem path to ch... |
| metrics | `get_histogram_stats` | Get statistics for a named histogram.

Args:
    name: Histogram name.

Retur... |
| metrics | `get_report` | Get a full metrics report.

Returns:
    Dictionary with uptime, counters, ga... |
| metrics | `increment_counter` | Increment a named counter.

Args:
    name: Counter name.
    value: Amount t... |
| metrics | `record_histogram` | Record a value in a named histogram.

Args:
    name: Histogram name.
    val... |
| metrics | `reset` | Clear all collected metrics. |
| metrics | `set_gauge` | Set a named gauge to a value.

Args:
    name: Gauge name.
    value: Current... |
| metrics | `to_dict` | Serialize system metrics to a dictionary.

Returns:
    Dictionary representa... |
| models | `CrawlConfig` | Configuration for web crawling behavior. |
| models | `CrawledPage` | A page that has been crawled. |
| models | `IndexedPage` | Represents a crawled and indexed page. |
| models | `Interest` | Represents a user-defined interest to track. |
| models | `InterestType` | Type of interest to track. |
| models | `Page` | A page model for the search index. |
| models | `SearchResult` | Represents a search result. |
| models | `from_dict` | Create an Interest from a dictionary.

Args:
    data: Dictionary with intere... |
| models | `matches` | Check if text/url matches this interest. |
| models | `score` | Calculate relevance score for text. |
| models | `to_dict` | Serialize the interest to a dictionary.

Returns:
    Dictionary representati... |
| notifications | `ConsoleHandler` | Print notifications to console. |
| notifications | `FileHandler` | Write notifications to a log file. |
| notifications | `InMemoryHandler` | Store notifications in memory for testing/inspection. |
| notifications | `Notification` | A single notification event. |
| notifications | `NotificationHandler` | Abstract base for notification handlers. |
| notifications | `NotificationLevel` | Severity levels for notifications. |
| notifications | `NotificationManager` | Central notification manager that dispatches to handlers. |
| notifications | `NotificationType` | Types of notifications. |
| notifications | `add_filter` | Add a filter. Notifications passing the filter are dispatched. |
| notifications | `add_handler` | Add a notification handler. |
| notifications | `clear` | Clear all stored notifications.

Returns:
    Number of notifications cleared. |
| notifications | `close` | Clean up resources. |
| notifications | `from_dict` | Create a Notification from a dictionary.

Args:
    data: Dictionary with not... |
| notifications | `get_all` | Get all stored notifications.

Returns:
    List of all notifications. |
| notifications | `get_unread` | Get all unread notifications.

Returns:
    List of unread notifications. |
| notifications | `handle` | Handle a notification. Return True if handled successfully. |
| notifications | `mark_all_read` | Mark all notifications as read.

Returns:
    Number of notifications marked ... |
| notifications | `notify` | Dispatch a notification to all handlers. Returns count of successful deliveries. |
| notifications | `notify_crawl_complete` | Send a crawl complete notification. |
| notifications | `notify_crawl_error` | Send a crawl error notification. |
| notifications | `notify_interest_match` | Send an interest match notification. |
| notifications | `notify_new_content` | Send a new content notification. |
| notifications | `remove_handler` | Remove a notification handler. |
| notifications | `to_dict` | Serialize the notification to a dictionary.

Returns:
    Dictionary represen... |
| pagination | `PageParams` | Parameters for pagination. |
| pagination | `PageResult` | Paginated result set. |
| pagination | `Paginator` | Paginates a collection of items. |
| pagination | `end_index` | 1-based index of the last item on this page. |
| pagination | `get_page` | Get a specific page of results.

Args:
    page: 1-based page number.
    per... |
| pagination | `has_next` | Whether there is a next page. |
| pagination | `has_prev` | Whether there is a previous page. |
| pagination | `iterate_pages` | Get all pages as a list. |
| pagination | `limit` | Maximum number of items per page. |
| pagination | `next_page` | Page number of the next page, or None. |
| pagination | `offset` | Zero-based offset for database queries. |
| pagination | `prev_page` | Page number of the previous page, or None. |
| pagination | `start_index` | 1-based index of the first item on this page. |
| pagination | `to_dict` | Serialize the page result to a dictionary.

Returns:
    Dictionary represent... |
| pagination | `total_items` | Total number of items in the collection. |
| pagination | `total_pages` | Total number of pages. |
| performance_monitor | `MetricSample` | A single metric data point. |
| performance_monitor | `MetricStats` | Aggregated statistics for a metric. |
| performance_monitor | `PerformanceMonitor` | Monitors and tracks performance metrics. |
| performance_monitor | `TimerContext` | Context manager for timing operations. |
| performance_monitor | `elapsed` | Seconds elapsed since the timer started. |
| performance_monitor | `get_all_stats` | Get stats for all tracked metrics. |
| performance_monitor | `get_recent_samples` | Get recent samples for a metric. |
| performance_monitor | `get_stats` | Get aggregated stats for a metric. |
| performance_monitor | `mean` | Arithmetic mean of recorded values. |
| performance_monitor | `p50` | Approximate 50th percentile (mean). |
| performance_monitor | `p95` | Approximate 95th percentile (mean * 1.5). |
| performance_monitor | `p99` | Approximate 99th percentile (mean * 2.0). |
| performance_monitor | `record` | Record a metric value. |
| performance_monitor | `reset` | Reset all metrics. |
| performance_monitor | `stddev` | Population standard deviation of recorded values. |
| performance_monitor | `timer` | Create a timer context manager. |
| pipeline | `ContentPipeline` | Sequential pipeline for processing content through multiple steps. |
| pipeline | `PipelineResult` | Result of running a pipeline. |
| pipeline | `PipelineStep` | A single step in the processing pipeline. |
| pipeline | `add_step` | Add a processing step to the pipeline. |
| pipeline | `clear` | Remove all steps from the pipeline. |
| pipeline | `disable_step` | Disable a step by name. |
| pipeline | `enable_step` | Enable a step by name. |
| pipeline | `enabled_steps` | Names of currently enabled steps. |
| pipeline | `execute` | Execute this step on the data. |
| pipeline | `get_step` | Get a step by name.

Args:
    name: The step name.

Returns:
    The Pipelin... |
| pipeline | `remove_step` | Remove a step by name. |
| pipeline | `run` | Run the pipeline on the given data. |
| pipeline | `step_count` | Total number of steps in the pipeline. |
| progress | `ProgressState` | States of a progress tracker. |
| progress | `ProgressStep` | A single step within a progress operation. |
| progress | `ProgressStore` | Store and retrieve progress trackers. |
| progress | `ProgressTracker` | Track progress of a long-running operation. |
| progress | `advance` | Advance to the next step. |
| progress | `cancel` | Cancel the operation. |
| progress | `cleanup` | Remove old completed trackers. Returns count removed. |
| progress | `complete` | Mark the operation as completed. |
| progress | `create` | Create a new progress tracker. |
| progress | `elapsed_seconds` | Get elapsed time in seconds. |
| progress | `estimated_remaining` | Estimate remaining time in seconds. |
| progress | `fail` | Mark the operation as failed. |
| progress | `format_bar` | Format a progress bar string. |
| progress | `from_dict` | Create a ProgressTracker from a dictionary, ignoring extra keys. |
| progress | `get` | Get a tracker by ID. |
| progress | `list_active` | List all active (running/paused) trackers. |
| progress | `list_completed` | List completed trackers, most recent first. |
| progress | `load_all` | Load trackers from disk. Returns count loaded. |
| progress | `pause` | Pause the operation. |
| progress | `progress_percent` | Get progress as percentage (0-100). |
| progress | `remove` | Remove a tracker. |
| progress | `resume` | Resume a paused operation. |
| progress | `save_all` | Save all trackers to disk. |
| progress | `set_message` | Set a status message. |
| progress | `set_total` | Set the total number of steps. |
| progress | `start` | Start the operation. |
| progress | `to_dict` | Serialize the progress step to a dictionary.

Returns:
    Dictionary represe... |
| queue | `Task` | A unit of work in the task queue. |
| queue | `TaskPriority` | Priority levels for tasks in the queue. |
| queue | `TaskQueue` | Thread-safe priority task queue. |
| queue | `TaskStatus` | Possible statuses for a task. |
| queue | `cancel` | Mark the task as cancelled. |
| queue | `cancel_task` | Cancel a pending task.

Args:
    task_id: The task identifier.

Returns:
   ... |
| queue | `clear_completed` | Trim the completed task list, keeping only the most recent.

Args:
    keep: ... |
| queue | `complete` | Mark the task as completed with an optional result. |
| queue | `complete_task` | Mark a running task as completed.

Args:
    task_id: The task identifier.
  ... |
| queue | `completed_count` | Number of completed tasks retained. |
| queue | `dequeue` | Remove and return the highest-priority pending task.

Returns:
    The next T... |
| queue | `duration` | Elapsed time in seconds between start and completion, or None. |
| queue | `enqueue` | Add a task to the queue.

Args:
    task_id: Unique identifier for the task.
... |
| queue | `fail` | Mark the task as failed with an error message. |
| queue | `fail_task` | Mark a running task as failed.

Args:
    task_id: The task identifier.
    e... |
| queue | `get_stats` | Get queue statistics.

Returns:
    Dictionary with queue size, task counts, ... |
| queue | `get_task` | Look up a task by ID.

Args:
    task_id: The task identifier.

Returns:
    ... |
| queue | `pending_count` | Number of tasks still in PENDING status. |
| queue | `size` | Number of tasks in the heap (including non-pending). |
| queue | `start` | Mark the task as running and record start time. |
| rate_limiter | `RateLimitConfig` | Configuration for rate limiting. |
| rate_limiter | `RateLimitStatus` | Current status of rate limiting. |
| rate_limiter | `RateLimiter` | Rate limiter that manages limits per domain. |
| rate_limiter | `TokenBucket` | Token bucket rate limiter for a single domain. |
| rate_limiter | `acquire` | Try to acquire a token. Returns True if successful. |
| rate_limiter | `can_request` | Check if a request to the domain is allowed. |
| rate_limiter | `get_all_statuses` | Get rate limit status for all tracked domains. |
| rate_limiter | `get_status` | Get rate limit status for a domain. |
| rate_limiter | `get_wait_time` | Get wait time for a domain. |
| rate_limiter | `reset_all` | Reset all rate limits. |
| rate_limiter | `reset_domain` | Reset rate limit for a domain. |
| rate_limiter | `set_domain_config` | Set rate limit config for a specific domain. |
| rate_limiter | `status` | Get current rate limit status. |
| rate_limiter | `wait_for_request` | Wait until a request can be made, or timeout. |
| rate_limiter | `wait_time` | Get time to wait before next request can be made. |
| results | `ResultsExporter` | Export search results to various formats. |
| results | `ResultsFormatter` | Formats search results for display. |
| results | `SearchResult` | A formatted search result. |
| results | `create_snippet` | Create a snippet highlighting the query. |
| results | `format_result` | Format a single search result. |
| results | `format_results` | Format multiple search results. |
| results | `search_and_format` | Search index and format results. |
| results | `to_csv` | Export results as CSV. |
| results | `to_json` | Export results as JSON. |
| results | `to_markdown` | Export results as Markdown. |
| robots_cache | `RobotsCache` | Thread-safe cache for robots.txt results. |
| robots_cache | `RobotsCacheEntry` | Cached robots.txt parsing result. |
| robots_cache | `allows_agent` | Check if a user agent is allowed based on cached robots.txt rules.

Args:
   ... |
| robots_cache | `domains` | List of all cached domains. |
| robots_cache | `get` | Get a cached robots.txt entry for a domain.

Args:
    domain: The domain to ... |
| robots_cache | `get_stats` | Get cache statistics.

Returns:
    Dictionary with cache size, TTL, max entr... |
| robots_cache | `invalidate` | Remove a domain from the cache.

Args:
    domain: The domain to invalidate.
... |
| robots_cache | `invalidate_all` | Clear all cached entries. |
| robots_cache | `is_expired` | Check if this cache entry has exceeded its TTL.

Args:
    ttl: Time-to-live ... |
| robots_cache | `put` | Store a robots.txt cache entry.

Args:
    entry: The cache entry to store. |
| robots_cache | `size` | Number of entries in the cache. |
| robots_parser | `RobotsPolicy` | Parsed robots.txt policy for a domain. |
| robots_parser | `RobotsRule` | A single robots.txt rule. |
| robots_parser | `can_fetch` | Check if a URL can be fetched according to robots.txt. |
| robots_parser | `is_allowed` | Check if a URL is allowed by a robots policy. |
| robots_parser | `parse_robots_txt` | Parse robots.txt content into a RobotsPolicy. |
| rss | `Feed` | A parsed RSS/Atom feed. |
| rss | `FeedEntry` | A single entry from an RSS/Atom feed. |
| rss | `RSSParser` | Parse RSS 2.0 and Atom feeds. |
| rss | `entry_count` | Number of entries in this feed. |
| rss | `get_recent_entries` | Get the most recent entries. |
| rss | `is_feed` | Check if XML content appears to be a feed. |
| rss | `parse` | Parse RSS or Atom feed XML content. |
| rss | `to_dict` | Convert to dictionary. |
| scheduler | `ScheduleConfig` | Configuration for a scheduled crawl job. |
| scheduler | `ScheduleEntry` | A scheduled crawl entry. |
| scheduler | `ScheduleStore` | Persistent storage for schedule entries. |
| scheduler | `ScheduledJob` | A scheduled crawl job (CLI-facing). |
| scheduler | `Scheduler` | Manages scheduled crawling jobs. |
| scheduler | `add` | Add a schedule entry. |
| scheduler | `add_job` | Add a scheduled job (alias for add_schedule, CLI-compatible). |
| scheduler | `add_schedule` | Add a new scheduled crawl job. |
| scheduler | `get` | Get a schedule entry by name. |
| scheduler | `get_due_schedules` | Get all schedules that are due to run. |
| scheduler | `list_all` | List all schedule entries. |
| scheduler | `list_jobs` | List all scheduled jobs. |
| scheduler | `remove` | Remove a schedule entry by name. |
| scheduler | `remove_job` | Remove a scheduled job (alias for remove_schedule, CLI-compatible). |
| scheduler | `remove_schedule` | Remove a scheduled crawl job. |
| scheduler | `run_schedule` | Run a scheduled crawl job. Returns pages indexed. |
| scheduler | `toggle_schedule` | Toggle a schedule's enabled status. |
| scheduler | `update` | Update a schedule entry. |
| scheduler | `update_next_run_times` | Update next_run times based on last_run. |
| scraper | `HTMLScraper` | Scraps HTML content and extracts structured data. |
| scraper | `ScrapedContent` | Content extracted from an HTML page. |
| scraper | `ScraperConfig` | Configuration for HTML scraping. |
| scraper | `scrape` | Scrape HTML content and return structured data. |
| search_index | `SearchIndex` | In-memory search index with JSON persistence. |
| search_index | `add` | Add a page to the index. |
| search_index | `clear` | Clear the entire index. |
| search_index | `count` | Return number of indexed pages. |
| search_index | `get` | Get a page by URL. |
| search_index | `remove` | Remove a page from the index. |
| search_index | `search` | Search and return (url, score) tuples by relevance. |
| search_index | `urls` | Return list of all indexed URLs. |
| search_suggestions | `SearchSuggestions` | Generates search suggestions from indexed content metadata. |
| search_suggestions | `Suggestion` | A single search suggestion. |
| search_suggestions | `add_keywords` | Add extracted keywords for suggestion generation. |
| search_suggestions | `add_search_history` | Add queries to search history. |
| search_suggestions | `add_tags` | Add tags for suggestion generation. |
| search_suggestions | `clear` | Clear all suggestion data. |
| search_suggestions | `from_dict` | Deserialize suggestion data. |
| search_suggestions | `get_related_queries` | Get queries related to the given query (from history). |
| search_suggestions | `get_trending` | Get the most trending search queries. |
| search_suggestions | `record_search` | Record a single search query. |
| search_suggestions | `suggest` | Generate suggestions for a given prefix. |
| search_suggestions | `to_dict` | To_dict. |
| serializer | `DeserializationError` | Raised when deserialization fails. |
| serializer | `SerializationConfig` | Configuration for serialization. |
| serializer | `SerializationError` | Raised when serialization fails. |
| serializer | `Serializer` | Handles serialization of data to various formats. |
| serializer | `from_csv` | Deserialize CSV string to list of dicts. |
| serializer | `from_json` | Deserialize JSON string to dict. |
| serializer | `to_csv` | Serialize list of dicts to CSV string. |
| serializer | `to_dict` | Convert dataclass or object to dict. |
| serializer | `to_json` | Serialize data to JSON string. |
| session | `CrawlSession` | Represents a single crawl session. |
| session | `SessionManager` | Manages crawl sessions with persistence. |
| session | `SessionStats` | Statistics for a crawl session. |
| session | `SessionStatus` | Possible statuses for a crawl session. |
| session | `complete` | Mark the session as completed. |
| session | `create_session` | Create a new crawl session.

Args:
    session_id: Unique session identifier.... |
| session | `duration` | Elapsed time in seconds since the session started. |
| session | `fail` | Mark the session as failed with an error message. |
| session | `get_active_session` | Get the currently active session.

Returns:
    The active CrawlSession, or N... |
| session | `get_session` | Get a session by ID.

Args:
    session_id: The session identifier.

Returns:... |
| session | `list_active` | List all active sessions.

Returns:
    List of active CrawlSession objects. |
| session | `list_sessions` | List all sessions.

Returns:
    List of all CrawlSession objects. |
| session | `load_session` | Load a session from disk.

Args:
    filepath: Path to the session JSON file.... |
| session | `pause` | Pause the session if currently active. |
| session | `record_page_indexed` | Record that a page was indexed. |
| session | `record_url_crawled` | Record a successfully crawled URL.

Args:
    url: The URL that was crawled.
... |
| session | `record_url_failed` | Record a failed URL crawl.

Args:
    url: The URL that failed.
    error: Op... |
| session | `record_url_skipped` | Record a skipped URL.

Args:
    url: The URL that was skipped. |
| session | `remove_session` | Remove a session.

Args:
    session_id: The session to remove.

Returns:
   ... |
| session | `resume` | Resume the session if currently paused. |
| session | `save_session` | Save a session to disk.

Args:
    session_id: The session to save.

Returns:... |
| session | `session_count` | Number of sessions managed. |
| session | `set_active` | Set a session as the active one.

Args:
    session_id: The session to activa... |
| session | `stop` | Stop the session (user-initiated halt). |
| session | `success_rate` | Ratio of successfully crawled URLs to total attempted. |
| session | `to_dict` | Serialize session stats to a dictionary.

Returns:
    Dictionary representat... |
| session | `total_processed` | Total number of URLs processed (crawled + failed + skipped). |
| similarity | `SimilarityEngine` | Detects content similarity using multiple algorithms. |
| similarity | `SimilarityResult` | Result of a similarity comparison. |
| similarity | `compare` | Compare two texts for similarity. |
| similarity | `find_duplicates` | Find duplicate pairs in a list of texts. |
| similarity | `is_similar` | Check if two texts are similar above threshold. |
| sitemap | `Sitemap` | Parsed sitemap data. |
| sitemap | `SitemapEntry` | A single entry from a sitemap. |
| sitemap | `SitemapParser` | Parse XML sitemaps and sitemap indexes. |
| sitemap | `filter_by_changefreq` | Filter sitemap entries by change frequency. |
| sitemap | `filter_by_priority` | Filter sitemap entries by minimum priority. |
| sitemap | `get_recent_entries` | Get entries modified within the last N days. |
| sitemap | `get_urls` | Get all URLs from entries. |
| sitemap | `is_valid` | Check if the entry has a valid location. |
| sitemap | `parse` | Parse sitemap XML content. |
| sitemap | `parse_text_sitemap` | Parse a plain text sitemap (one URL per line). |
| sitemap | `sitemap_count` | Number of nested sitemaps. |
| sitemap | `url_count` | Number of URLs in this sitemap. |
| stats | `CrawlStats` | Statistics about crawling activity. |
| stats | `IndexStats` | Statistics about the search index. |
| stats | `StatsCollector` | Collects and reports statistics. |
| stats | `format_index_stats` | Format index statistics as a string. |
| stats | `get_index_stats` | Calculate current index statistics. |
| storage | `Storage` | File-based storage for interests, config, and indexed pages. |
| storage | `add_interest` | Add a new interest. |
| storage | `add_page` | Add or update an indexed page. |
| storage | `clear_pages` | Clear all indexed pages. |
| storage | `get_config` | Get crawl configuration. |
| storage | `get_interest` | Get a single interest by name. |
| storage | `get_interests` | Get all interests. |
| storage | `get_page` | Get a single page by URL. |
| storage | `get_page_count` | Get total number of indexed pages. |
| storage | `get_pages` | Get all indexed pages. |
| storage | `get_stats` | Get storage statistics. |
| storage | `list_interests` | List all interests with summary info. |
| storage | `remove_interest` | Remove an interest by name. |
| storage | `remove_page` | Remove a page by URL. |
| storage | `save_config` | Save crawl configuration. |
| summarizer | `SummaryResult` | Result of content summarization. |
| summarizer | `TextSummarizer` | Extractive text summarization using various methods. |
| summarizer | `summarize` | Generate a summary of the text. |
| summarizer | `truncate` | Truncate text to a maximum length. |
| tags | `Tag` | A tag that can be applied to pages. |
| tags | `TagStore` | Persistent storage for tags and their page associations. |
| tags | `add_tag_to_page` | Add a tag to a page. Returns False if tag doesn't exist. |
| tags | `clear` | Clear all tags and associations. |
| tags | `create_tag` | Create a new tag. |
| tags | `delete_tag` | Delete a tag and remove it from all pages. |
| tags | `get_pages_for_tag` | Get all pages with a specific tag. |
| tags | `get_tag` | Get a tag by name. |
| tags | `get_tag_count` | Get total number of tags. |
| tags | `get_tagged_page_count` | Get number of pages that have at least one tag. |
| tags | `get_tags_for_page` | Get all tags for a page. |
| tags | `list_tags` | List all tags. |
| tags | `remove_tag_from_page` | Remove a tag from a page. |
| tags | `search_by_tag` | Search for pages by tag name (alias for get_pages_for_tag). |
| text_utils | `count_characters` | Count characters in text.

Args:
    text: Input text.
    include_spaces: Wh... |
| text_utils | `count_words` | Count words in text.

Args:
    text: Input text.

Returns:
    Number of words. |
| text_utils | `extract_keywords` | Extract top keywords from text by frequency.

Args:
    text: Input text.
   ... |
| text_utils | `extract_paragraphs` | Split text into paragraphs.

Args:
    text: Input text.
    min_length: Mini... |
| text_utils | `extract_sentences` | Split text into sentences.

Args:
    text: Input text.
    min_length: Minim... |
| text_utils | `highlight_text` | Highlight search terms in text.

Args:
    text: Input text.
    terms: List ... |
| text_utils | `levenshtein_distance` | Calculate Levenshtein edit distance between two strings.

Args:
    s1: First... |
| text_utils | `normalize_whitespace` | Collapse all whitespace sequences into single spaces and strip.

Args:
    te... |
| text_utils | `read_time_minutes` | Estimate reading time in minutes.

Args:
    text: Input text.
    wpm: Words... |
| text_utils | `remove_html_tags` | Strip HTML tags from text, preserving content.

Args:
    html: HTML string t... |
| text_utils | `similarity_ratio` | Calculate similarity ratio between two strings (0.0 to 1.0).

Uses Levenshtei... |
| text_utils | `slugify` | Convert text to URL-friendly slug.

Args:
    text: Input text.

Returns:
   ... |
| text_utils | `tokenize` | Tokenize text into words.

Args:
    text: Input text.
    lowercase: Whether... |
| text_utils | `truncate_text` | Truncate text to a maximum length without breaking words.

Args:
    text: Te... |
| text_utils | `word_frequency` | Calculate word frequency in text.

Args:
    text: Input text.
    min_freq: ... |
| tfidf | `TfidfScorer` | Compute TF-IDF scores for documents and queries. |
| tfidf | `add_document` | Add a document to the corpus. Returns document ID. |
| tfidf | `clear` | Clear the corpus. |
| tfidf | `compute_tfidf` | Compute TF-IDF scores for a document. |
| tfidf | `document_count` | Return number of documents in corpus. |
| tfidf | `get_top_terms` | Get top N terms by TF-IDF score for a document. |
| tfidf | `rank_documents` | Rank all documents by relevance to query. |
| tfidf | `remove_document` | Remove a document from the corpus. |
| tfidf | `score_query` | Score a document against a query using TF-IDF dot product. |
| tfidf | `vocabulary_size` | Return size of vocabulary. |
| throttle | `ThrottleManager` | Manages request throttling across multiple domains. |
| throttle | `ThrottleRule` | Rate limiting rule for a domain. |
| throttle | `ThrottleState` | Tracks throttle state for a domain. |
| throttle | `get_rule` | Process get_rule.

Args:
domain. |
| throttle | `get_stats` | Process get_stats.

Args:
domain. |
| throttle | `rate_per_second` | Rate_per_second. |
| throttle | `reset` | Reset throttle counters.

Args:
    domain: Specific domain to reset, or None... |
| throttle | `set_rule` | Process set_rule.

Args:
domain, rule. |
| throttle | `should_throttle` | Process should_throttle.

Args:
url. |
| throttle | `wait_if_needed` | Wait if throttling is needed, return wait time in seconds. |
| url_classifier | `ClassificationResult` | Result of URL classification. |
| url_classifier | `URLCategory` | URLCategory. |
| url_classifier | `URLClassifier` | Classifies URLs into categories based on patterns. |
| url_classifier | `api_re` | Api_re. |
| url_classifier | `classify` | Classify a URL into a category. |
| url_classifier | `classify_batch` | Classify multiple URLs. |
| url_classifier | `feed_re` | Feed_re. |
| url_classifier | `get_category_counts` | Get count of URLs per category. |
| url_classifier | `media_re` | Media_re. |
| url_classifier | `redirect_re` | Redirect_re. |
| url_classifier | `static_re` | Static_re. |
| url_dedup | `DedupResult` | Result of deduplication check. |
| url_dedup | `URLDeduplicator` | Deduplicate URLs using normalization and fuzzy matching. |
| url_dedup | `add_url` | Add a URL and check if it's a duplicate. |
| url_dedup | `check_duplicate` | Check if a URL is a duplicate of a previously seen URL. |
| url_dedup | `clear` | Clear all seen URLs. |
| url_dedup | `deduplicate_urls` | Deduplicate a list of URLs, returning unique URLs and results. |
| url_dedup | `get_canonical_url` | Get the canonical (first seen) URL for a given URL. |
| url_dedup | `get_domain_urls` | Get all URLs for a specific domain. |
| url_dedup | `get_duplicates` | Get all detected duplicates grouped by canonical URL. |
| url_dedup | `get_stats` | Get deduplication statistics. |
| url_dedup | `normalize_url` | Normalize a URL for comparison. |
| url_dedup | `seen_count` | Seen_count. |
| url_filter | `UrlFilter` | Filter URLs based on blacklist and whitelist rules.

Whitelist rules take pre... |
| url_filter | `UrlFilterRule` | A single URL filter rule. |
| url_filter | `add_blacklist` | Add a URL pattern to the blacklist. |
| url_filter | `add_whitelist` | Add a URL pattern to the whitelist. |
| url_filter | `blacklist_count` | Number of blacklist rules. |
| url_filter | `clear` | Clear all rules. |
| url_filter | `clear_blacklist` | Clear all blacklist rules. |
| url_filter | `clear_whitelist` | Clear all whitelist rules. |
| url_filter | `filter_urls` | Filter a list of URLs, returning only allowed ones.

Args:
    urls: List of ... |
| url_filter | `get_blocked_urls` | Return URLs that are blocked.

Args:
    urls: List of URLs to check.

Return... |
| url_filter | `get_matching_rule` | Get the first matching rule for a URL, or None.

Args:
    url: URL to check.... |
| url_filter | `is_allowed` | Check if a URL is allowed (passes all filters).

Args:
    url: URL to check.... |
| url_filter | `is_blocked` | Check if a URL is blocked.

Args:
    url: URL to check.

Returns:
    True i... |
| url_filter | `matches` | Check if URL matches this rule's pattern. |
| url_filter | `whitelist_count` | Number of whitelist rules. |
| url_history | `URLHistory` | Track URL visit history with persistence. |
| url_history | `URLVisit` | Record of a single URL visit. |
| url_history | `clear` | Clear all history. Returns count of cleared entries. |
| url_history | `from_dict` | Process from_dict.

Args:
data. |
| url_history | `get_domain_stats` | Get visit counts grouped by domain. |
| url_history | `get_stats` | Get statistics about URL history. |
| url_history | `get_unique_urls` | Get list of unique URLs visited. |
| url_history | `get_visits` | Get visit records, optionally filtered by URL and time. |
| url_history | `load` | Load history from file. Returns count loaded. |
| url_history | `record` | Record a URL visit. |
| url_history | `save` | Save history to file. |
| url_history | `to_dict` | To_dict. |
| url_normalizer | `get_domain` | Extract the domain from a URL. |
| url_normalizer | `get_fragment` | Extract the fragment from a URL. |
| url_normalizer | `get_path` | Extract the path from a URL. |
| url_normalizer | `get_query_string` | Extract the query string from a URL. |
| url_normalizer | `is_canonical` | Check if a URL is already in canonical form. |
| url_normalizer | `normalize_url` | Normalize a URL by applying standard transformations. |
| url_normalizer | `resolve_relative_url` | Resolve a relative URL against a base URL. |
| url_normalizer | `strip_tracking_params` | Remove common tracking parameters from a URL. |
| url_normalizer | `urls_are_equivalent` | Check if two URLs are equivalent after normalization. |
| url_utils | `extract_all_urls` | Extract all URLs from HTML content or plain text.

If base_url is not provide... |
| url_utils | `extract_domain` | Extract domain from URL. |
| url_utils | `extract_subdomain` | Extract subdomain from URL. |
| url_utils | `get_tld` | Extract top-level domain from URL. |
| url_utils | `is_excluded_url` | Check if URL should be excluded from crawling. |
| url_utils | `is_internal_link` | Check if URL is an internal link relative to base URL. |
| url_utils | `is_robotstxt` | Check if URL is a robots.txt file. |
| url_utils | `is_same_domain` | Check if two URLs are on the same domain. |
| url_utils | `is_sitemap` | Check if URL is a sitemap file. |
| url_utils | `is_valid_url` | Check if a URL is valid and has an http/https scheme. |
| url_utils | `join_urls` | Join a base URL with a relative URL.

If base ends with a path (not /), relat... |
| url_utils | `normalize_url` | Normalize URL: lowercase scheme/domain, remove fragments, default ports. |
| url_utils | `remove_query_params` | Remove specific query parameters from URL. |
| url_utils | `url_to_path` | Convert URL to a filesystem-safe path. |
| validator | `ContentValidator` | Validates extracted content quality. |
| validator | `URLValidator` | Validates URLs for crawling. |
| validator | `ValidationResult` | Result of a validation check. |
| validator | `add_error` | Process add_error.

Args:
message. |
| validator | `add_warning` | Process add_warning.

Args:
message. |
| validator | `validate` | Process validate.

Args:
url. |
| validator | `validate_batch` | Validate multiple URLs. |
| versioning | `ContentVersion` | A versioned snapshot of content. |
| versioning | `VersionTracker` | Tracks content versions and detects changes. |
| versioning | `clear` | Clear versions for a URL or all URLs. |
| versioning | `compute_hash` | Compute SHA-256 hash of content. |
| versioning | `generate_version_id` | Generate a unique version ID from URL and content hash. |
| versioning | `get_all_urls` | Get all tracked URLs. |
| versioning | `get_change_count` | Get the number of version changes for a URL. |
| versioning | `get_latest` | Get the latest version for a URL. |
| versioning | `get_versions` | Get all versions for a URL. |
| versioning | `has_changed` | Check if new content differs from the latest version. |
| versioning | `record_version` | Record a new version of content for a URL. |
| versioning | `to_dict` | To_dict. |
| versioning | `total_versions` | Total number of versions tracked. |
| versioning | `tracked_urls` | Number of URLs being tracked. |
| webhook | `WebhookConfig` | Configuration for a webhook endpoint. |
| webhook | `WebhookEvent` | WebhookEvent. |
| webhook | `WebhookPayload` | Payload sent to webhook endpoints. |
| webhook | `WebhookSender` | Sends webhook notifications to configured endpoints. |
| webhook | `add_endpoint` | Process add_endpoint.

Args:
config. |
| webhook | `endpoint_count` | Endpoint_count. |
| webhook | `remove_endpoint` | Process remove_endpoint.

Args:
url. |
| webhook | `send` | Send a webhook payload to all matching endpoints. |
| webhook | `should_send` | Process should_send.

Args:
event. |
| webhook | `to_dict` | To_dict. |
| webhook | `to_json` | To_json. |
