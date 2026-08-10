# Modules

### __init__
- **Purpose**: personal-index: A personal web search engine that scans, filters, and indexes the web for you.
- **Path**: `personal_index.__init__`

### analytics
- **Purpose**: Analytics module for personal index usage tracking.
- **Path**: `personal_index.analytics`

### annotation
- **Purpose**: Content annotation system for marking and categorizing indexed content.
- **Path**: `personal_index.annotation`

### backup
- **Purpose**: Backup and restore system for personal index data.
- **Path**: `personal_index.backup`

### bookmark_export
- **Purpose**: Bookmark export module for exporting saved bookmarks as HTML, JSON, and OPML.
- **Path**: `personal_index.bookmark_export`

### bookmarks
- **Purpose**: Bookmark management for personal index.
- **Path**: `personal_index.bookmarks`

### cache
- **Purpose**: Caching utilities with LRU and TTL strategies.
- **Path**: `personal_index.cache`

### cli
- **Purpose**: CLI interface for personal-index.
- **Path**: `personal_index.cli`

### content
- **Purpose**: Content extraction and text processing for personal-index.
- **Path**: `personal_index.content`

### content_annotations
- **Purpose**: Content annotations module - user notes on saved items.
- **Path**: `personal_index.content_annotations`

### content_categorizer
- **Purpose**: Content categorizer module for classifying saved items by topic.

Analyzes content text, titles, URLs, and metadata to assign topic categories
with confidence scores. Uses rule-based keyword matching with multiple signals.
- **Path**: `personal_index.content_categorizer`

### content_collections
- **Purpose**: Content collections module - group saved items into collections.
- **Path**: `personal_index.content_collections`

### content_dedup
- **Purpose**: Content deduplication - detect duplicate saved content.
- **Path**: `personal_index.content_dedup`

### content_enricher
- **Purpose**: Content enrichment module for enhancing indexed content with metadata.
- **Path**: `personal_index.content_enricher`

### content_export_csv
- **Purpose**: Content export as CSV for personal-index.
- **Path**: `personal_index.content_export_csv`

### content_extractor
- **Purpose**: Content extraction from HTML pages.
- **Path**: `personal_index.content_extractor`

### content_favicon
- **Purpose**: Content favicon module - extract favicons from saved URLs.
- **Path**: `personal_index.content_favicon`

### content_feed
- **Purpose**: RSS/Atom feed generation for personal-index recent saves.
- **Path**: `personal_index.content_feed`

### content_filter
- **Purpose**: Content filtering based on user interests.
- **Path**: `personal_index.content_filter`

### content_health
- **Purpose**: Content health monitoring for personal index.

Provides a lightweight health check for the content subsystem,
returning status, timestamp, and a numeric score.

Also provides URL accessibility checking for saved content URLs.
- **Path**: `personal_index.content_health`

### content_import_html
- **Purpose**: Content import HTML module - import Netscape HTML bookmarks.
- **Path**: `personal_index.content_import_html`

### content_priority
- **Purpose**: Content priority scoring - score content importance.
- **Path**: `personal_index.content_priority`

### content_scheduler
- **Purpose**: Schedule periodic content re-indexing and updates.
- **Path**: `personal_index.content_scheduler`

### content_scoring
- **Purpose**: Content scoring module for ranking indexed content by quality.
- **Path**: `personal_index.content_scoring`

### content_search_fulltext
- **Purpose**: Full-text search with ranking for personal-index content.
- **Path**: `personal_index.content_search_fulltext`

### content_social_preview
- **Purpose**: Content social preview module - generate social media preview cards.
- **Path**: `personal_index.content_social_preview`

### content_summarizer
- **Purpose**: Content summarizer - extract key points from saved articles.
- **Path**: `personal_index.content_summarizer`

### content_thumbnail
- **Purpose**: Content thumbnail module - generate thumbnails for saved items.
- **Path**: `personal_index.content_thumbnail`

### content_type
- **Purpose**: Content type detection and classification utilities.
- **Path**: `personal_index.content_type`

### crawl_stats
- **Purpose**: Crawl statistics tracking and reporting.
- **Path**: `personal_index.crawl_stats`

### dedup
- **Purpose**: Content deduplication using hash-based similarity detection.
- **Path**: `personal_index.dedup`

### domains
- **Purpose**: Domain management for crawling rules.
- **Path**: `personal_index.domains`

### encoding
- **Purpose**: Text encoding detection and conversion utilities.
- **Path**: `personal_index.encoding`

### export
- **Purpose**: Export bookmarks and indexed content to various formats.
- **Path**: `personal_index.export`

### export_markdown
- **Purpose**: Export content as markdown, HTML, and plain text formats.
- **Path**: `personal_index.export_markdown`

### formatter
- **Purpose**: Output formatting utilities.
- **Path**: `personal_index.formatter`

### fuzzy_search
- **Purpose**: Fuzzy search for personal index.
- **Path**: `personal_index.fuzzy_search`

### health
- **Purpose**: Health check and diagnostics for personal index.
- **Path**: `personal_index.health`

### health_report
- **Purpose**: Comprehensive health report generation for personal-index.
- **Path**: `personal_index.health_report`

### importer
- **Purpose**: Import bookmarks and content from various formats.
- **Path**: `personal_index.importer`

### index
- **Purpose**: Search index module for CLI interface.
- **Path**: `personal_index.index`

### indexer
- **Purpose**: Search index module for personal-index.
- **Path**: `personal_index.indexer`

### interest_store
- **Purpose**: Interest storage and management.
- **Path**: `personal_index.interest_store`

### interests
- **Purpose**: Interest management module for CLI interface.
- **Path**: `personal_index.interests`

### keyword_extractor
- **Purpose**: Keyword extraction from text using frequency analysis.
- **Path**: `personal_index.keyword_extractor`

### link_analyzer
- **Purpose**: Link analysis for crawled pages.
- **Path**: `personal_index.link_analyzer`

### link_preview
- **Purpose**: Link preview module that generates Open Graph cards from URLs.

Extracts Open Graph (og:*) and Twitter Card meta tags from HTML,
falling back to standard meta tags when structured tags are missing.
- **Path**: `personal_index.link_preview`

### logging_config
- **Purpose**: Logging configuration for personal-index.
- **Path**: `personal_index.logging_config`

### metrics
- **Purpose**: System metrics collection and reporting.
- **Path**: `personal_index.metrics`

### models
- **Purpose**: Data models for personal-index.
- **Path**: `personal_index.models`

### notifications
- **Purpose**: Notification system for personal index events.
- **Path**: `personal_index.notifications`

### pagination
- **Purpose**: Pagination utilities for search and browse results.
- **Path**: `personal_index.pagination`

### performance_monitor
- **Purpose**: Performance monitoring and metrics collection.
- **Path**: `personal_index.performance_monitor`

### pipeline
- **Purpose**: Content processing pipeline for sequential transformations.
- **Path**: `personal_index.pipeline`

### progress
- **Purpose**: Progress tracking for long-running operations.
- **Path**: `personal_index.progress`

### queue
- **Purpose**: Priority task queue for managing crawl and index operations.
- **Path**: `personal_index.queue`

### rate_limiter
- **Purpose**: Rate limiting for web requests using token bucket algorithm.
- **Path**: `personal_index.rate_limiter`

### results
- **Purpose**: Search results formatting and export.
- **Path**: `personal_index.results`

### robots_cache
- **Purpose**: Caching layer for robots.txt parsing results.
- **Path**: `personal_index.robots_cache`

### robots_parser
- **Purpose**: Robots.txt parser for personal-index.
- **Path**: `personal_index.robots_parser`

### rss
- **Purpose**: RSS feed reader for personal index.
- **Path**: `personal_index.rss`

### scheduler
- **Purpose**: Scheduled crawling management.
- **Path**: `personal_index.scheduler`

### scraper
- **Purpose**: HTML page scraper with content extraction.
- **Path**: `personal_index.scraper`

### search_index
- **Purpose**: Local search index with full-text search and relevance scoring.
- **Path**: `personal_index.search_index`

### search_suggestions
- **Purpose**: Search suggestions module for providing autocomplete and related queries.
- **Path**: `personal_index.search_suggestions`

### serializer
- **Purpose**: Data serialization utilities for indexed content.
- **Path**: `personal_index.serializer`

### session
- **Purpose**: Crawl session tracking and management.
- **Path**: `personal_index.session`

### similarity
- **Purpose**: Content similarity detection using various algorithms.
- **Path**: `personal_index.similarity`

### sitemap
- **Purpose**: Sitemap parser for discovering URLs on websites.
- **Path**: `personal_index.sitemap`

### sitemap_builder
- **Purpose**: Sitemap XML generator for indexed URLs.
- **Path**: `personal_index.sitemap_builder`

### stats
- **Purpose**: Statistics collection and reporting.
- **Path**: `personal_index.stats`

### storage
- **Purpose**: Storage layer for personal-index using JSON files.
- **Path**: `personal_index.storage`

### summarizer
- **Purpose**: Content summarization utilities.
- **Path**: `personal_index.summarizer`

### tags
- **Purpose**: Tag/label system for organizing indexed pages.
- **Path**: `personal_index.tags`

### text_utils
- **Purpose**: Text processing utilities for content indexing.
- **Path**: `personal_index.text_utils`

### tfidf
- **Purpose**: TF-IDF scoring for document relevance ranking.
- **Path**: `personal_index.tfidf`

### throttle
- **Purpose**: Request throttling with per-domain rate limiting.
- **Path**: `personal_index.throttle`

### url_classifier
- **Purpose**: URL classification for categorizing crawled URLs.
- **Path**: `personal_index.url_classifier`

### url_dedup
- **Purpose**: URL deduplication with fuzzy matching and normalization.
- **Path**: `personal_index.url_dedup`

### url_filter
- **Purpose**: URL filtering with blacklist and whitelist support.
- **Path**: `personal_index.url_filter`

### url_history
- **Purpose**: URL history tracking for crawled and visited pages.
- **Path**: `personal_index.url_history`

### url_normalizer
- **Purpose**: URL normalization and canonicalization utilities.
- **Path**: `personal_index.url_normalizer`

### url_utils
- **Purpose**: URL utility functions for the personal index.
- **Path**: `personal_index.url_utils`

### validator
- **Purpose**: URL and content validation utilities.
- **Path**: `personal_index.validator`

### versioning
- **Purpose**: Content versioning and change detection.
- **Path**: `personal_index.versioning`

### webhook
- **Purpose**: Webhook notification system for external integrations.
- **Path**: `personal_index.webhook`

### __init__
- **Purpose**: Content tagging module - automatically tag content by detected topics.
- **Path**: `personal_index.content_tagger.__init__`

### detector
- **Purpose**: Topic detection engine for content tagging.
- **Path**: `personal_index.content_tagger.detector`

### tag
- **Purpose**: Tag data model for content tagging.
- **Path**: `personal_index.content_tagger.tag`

### tagger
- **Purpose**: High-level content tagging interface.
- **Path**: `personal_index.content_tagger.tagger`

### 001_initial_schema
- **Purpose**: Migration 001: Initial schema for pages and interests.
- **Path**: `personal_index.migrations.001_initial_schema`

### 002_add_indexes
- **Purpose**: Migration 002: Add full-text search indexes and bookmarks.
- **Path**: `personal_index.migrations.002_add_indexes`

### __init__
- **Purpose**: Database migrations module for personal-index.
- **Path**: `personal_index.migrations.__init__`

### base
- **Purpose**: Base migration framework for personal-index.
- **Path**: `personal_index.migrations.base`

### runner
- **Purpose**: Migration runner for executing and rolling back migrations.
- **Path**: `personal_index.migrations.runner`

### __init__
- **Purpose**: Configuration management for personal-index.
- **Path**: `personal_index.config.__init__`

### loader
- **Purpose**: Configuration loader and saver.
- **Path**: `personal_index.config.loader`

### models
- **Purpose**: Configuration data models.
- **Path**: `personal_index.config.models`

### __init__
- **Purpose**: Authentication system for personal-index.
- **Path**: `personal_index.auth.__init__`

### api_keys
- **Purpose**: API key management for personal-index authentication.
- **Path**: `personal_index.auth.api_keys`

### passwords
- **Purpose**: Password hashing and verification for personal-index.
- **Path**: `personal_index.auth.passwords`

### permissions
- **Purpose**: Permission and role management for personal-index.
- **Path**: `personal_index.auth.permissions`

### sessions
- **Purpose**: Session management for personal-index authentication.
- **Path**: `personal_index.auth.sessions`

### tokens
- **Purpose**: JWT token management for personal-index authentication.
- **Path**: `personal_index.auth.tokens`

### __init__
- **Purpose**: Search facets module - filterable search dimensions.
- **Path**: `personal_index.search_facets.__init__`

### facet
- **Purpose**: Facet data models for filterable search dimensions.
- **Path**: `personal_index.search_facets.facet`

### facet_builder
- **Purpose**: Build facets from document collections.
- **Path**: `personal_index.search_facets.facet_builder`

### faceted_search
- **Purpose**: Faceted search engine with filterable dimensions.
- **Path**: `personal_index.search_facets.faceted_search`

### __init__
- **Purpose**: Crawler package for personal-index.
- **Path**: `personal_index.crawler.__init__`

### main
- **Purpose**: Web crawler with configurable depth, politeness, and rate limiting.
- **Path**: `personal_index.crawler.main`

### robots
- **Purpose**: Robots.txt parser.
- **Path**: `personal_index.crawler.robots`

### __init__
- **Purpose**: Content archive module - compress old content.
- **Path**: `personal_index.content_archive.__init__`

### archive_entry
- **Purpose**: Archive entry data model.
- **Path**: `personal_index.content_archive.archive_entry`

### archiver
- **Purpose**: High-level content archiver - compress and manage old content.
- **Path**: `personal_index.content_archive.archiver`

### compressor
- **Purpose**: Compression utilities for content archiving.
- **Path**: `personal_index.content_archive.compressor`

### __init__
- **Purpose**: Utilities package.
- **Path**: `personal_index.utils.__init__`

### url_utils
- **Purpose**: URL utility functions.
- **Path**: `personal_index.utils.url_utils`

### __init__
- **Purpose**: Admin dashboard module for personal-index.
- **Path**: `personal_index.dashboard.__init__`

### aggregator
- **Purpose**: Data aggregation for the admin dashboard.
- **Path**: `personal_index.dashboard.aggregator`

### export
- **Purpose**: Export functionality for the admin dashboard.
- **Path**: `personal_index.dashboard.export`

### stats
- **Purpose**: Real-time statistics for the admin dashboard.
- **Path**: `personal_index.dashboard.stats`

### views
- **Purpose**: Dashboard view components for personal-index admin interface.
- **Path**: `personal_index.dashboard.views`

### __init__
- **Purpose**: API server module for personal-index.
- **Path**: `personal_index.api.__init__`

### handlers
- **Purpose**: Error handlers and middleware for the personal-index API.
- **Path**: `personal_index.api.handlers`

### middleware
- **Purpose**: API middleware for personal-index.
- **Path**: `personal_index.api.middleware`

### models
- **Purpose**: Request and response models for the personal-index API.
- **Path**: `personal_index.api.models`

### pagination
- **Purpose**: Pagination utilities for the personal-index API.
- **Path**: `personal_index.api.pagination`

### rate_limit_middleware
- **Purpose**: Rate limiting middleware for the API server.
- **Path**: `personal_index.api.rate_limit_middleware`

### routes
- **Purpose**: API route definitions for personal-index.
- **Path**: `personal_index.api.routes`

### server
- **Purpose**: FastAPI server for personal-index REST API.
- **Path**: `personal_index.api.server`

### __init__
- **Purpose**: Content filtering package.
- **Path**: `personal_index.filter.__init__`

### engine
- **Purpose**: Content filtering engine.
- **Path**: `personal_index.filter.engine`

### matcher
- **Purpose**: Content matching and interest filtering.
- **Path**: `personal_index.filter.matcher`

### __init__
- **Purpose**: Content linker module - find related saved items.
- **Path**: `personal_index.content_linker.__init__`

### link
- **Purpose**: Link data model for content linking.
- **Path**: `personal_index.content_linker.link`

### linker
- **Purpose**: High-level content linker - finds related saved items.
- **Path**: `personal_index.content_linker.linker`

### similarity
- **Purpose**: Similarity engine for finding related content items.
- **Path**: `personal_index.content_linker.similarity`

### __init__
- **Purpose**: Content timeline module - chronological view of saved items.
- **Path**: `personal_index.content_timeline.__init__`

### timeline
- **Purpose**: Timeline manager for chronological content view.
- **Path**: `personal_index.content_timeline.timeline`

### timeline_entry
- **Purpose**: Timeline entry data model.
- **Path**: `personal_index.content_timeline.timeline_entry`

### timeline_view
- **Purpose**: Timeline view renderer for chronological content display.
- **Path**: `personal_index.content_timeline.timeline_view`

