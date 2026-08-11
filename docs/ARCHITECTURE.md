# Personal Index Architecture

## System Overview

Personal Index is a modular content management toolkit organized around a
6-stage pipeline architecture. Each stage is independently testable and
composable.

## Architecture Diagram

```
  +---------+     +----------+     +--------+     +-------+     +-----+     +-------+
  | Crawl   | --> | Extract  | --> | Filter | --> | Score | --> | Tag | --> | Index |
  +---------+     +----------+     +--------+     +-------+     +-----+     +-------+
       |                |               |               |             |             |
  URL sources      HTML/MD/TXT     Quality check    Interest match  Auto-tag    Search
  Local files      Parsing         Length filter    Keyword match   Topic detect  Index
```

## Module Organization

### Core Pipeline (personal_index/)

- **pipeline_runner.py** - Main orchestrator, coordinates all 6 stages
- **pipeline.py** - Pipeline step definitions and execution
- **pipeline_e2e.py** - End-to-end pipeline test utilities
- **pipeline_orchestrator.py** - Advanced pipeline orchestration
- **pipeline_runner.py** - Configurable pipeline execution engine

### CLI Layer (personal_index/cli*.py)

- **cli.py** - Main CLI entry point with Click command group
- **cli_pipeline.py** - Pipeline command implementation
- **cli_search.py** - Search command implementation
- **cli_import.py** - File import command
- **cli_export.py** - Export command (JSON, Markdown, CSV)
- **cli_interests.py** - Interest management commands
- **cli_tags.py** - Tag management commands
- **cli_crawl.py** - Standalone crawl command
- **cli_extract.py** - Content extraction command
- **cli_score.py** - Content scoring command
- **cli_stats.py** - Statistics command
- **cli_status.py** - Status command
- **cli_list.py** - List pages command
- **cli_remove.py** - Remove page command
- **cli_clear.py** - Clear index command
- **cli_top.py** - Top pages command
- **cli_verify.py** - Verification command
- **cli_watch.py** - Directory watch command
- **cli_schedule.py** - Scheduled crawl management
- **cli_doctor.py** - Health check command

### Data Layer

- **index.py** - SearchIndex: in-memory search with JSON persistence
- **interests.py** - InterestStore: persistent interest management
- **tags.py** - TagStore: persistent tag management
- **models.py** - Data models (CrawledPage, Interest, IndexedPage, etc.)
- **storage.py** - Generic storage utilities
- **cache.py** - Caching layer

### Processing Layer

- **crawler/main.py** - Web crawler with depth control and politeness
- **content_extractor.py** - Content extraction from HTML/MD/TXT
- **content_filter.py** - Content filtering by quality and interests
- **content_scoring.py** - Multi-factor content scoring engine
- **content_search.py** - Search with relevance ranking
- **keyword_extractor.py** - Keyword extraction from content
- **text_utils.py** - Text processing utilities

### Configuration

- **config/pipeline_config.py** - Pipeline configuration dataclass
- **config.yaml** - User configuration file

### Supporting Modules

- **analytics.py** - Usage analytics
- **backup.py** - Index backup and restore
- **bookmarks.py** - Bookmark management
- **content_dedup.py** - Content deduplication
- **content_versioning.py** - Content version tracking
- **fuzzy_search.py** - Fuzzy string matching
- **pagination.py** - Result pagination
- **rate_limiter.py** - Request rate limiting
- **scheduler.py** - Scheduled crawl management
- **sitemap.py** - Sitemap generation and parsing
- **tfidf.py** - TF-IDF scoring
- **url_classifier.py** - URL type classification
- **url_dedup.py** - URL deduplication
- **url_filter.py** - URL filtering
- **url_history.py** - URL crawl history tracking
- **webhook.py** - Webhook notifications

## Data Flow

1. **Input**: URLs or file paths
2. **Crawl**: Fetch content, extract links, respect robots.txt
3. **Extract**: Parse HTML/Markdown, extract text and metadata
4. **Filter**: Apply content length, domain, and interest filters
5. **Score**: Calculate relevance based on interests and quality
6. **Tag**: Auto-tag based on keywords and topics
7. **Index**: Add to searchable index with word-level indexing
8. **Output**: Search results, exports, statistics

## Persistence

All data is persisted to JSON files in the data directory:

- `search_index.json` - Full search index with word index
- `interests.json` - User-defined interests
- `tags.json` - Content tags
- `schedules.json` - Scheduled crawl jobs
- `cache/` - Cached crawl results
- `archive/` - Archived content
- `backups/` - Index backups

## Design Principles

1. **Modularity**: Each pipeline stage is a separate, testable module
2. **Composability**: Stages can be run independently or as a full pipeline
3. **Persistence**: All state is persisted to disk between runs
4. **Configurability**: All thresholds and weights are configurable
5. **CLI-first**: All functionality accessible via command line
