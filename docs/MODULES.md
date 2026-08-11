# Module Documentation

## Core Modules

### `personal_index.models`

Core data models for the application.

**Key Classes:**
- `Interest` - User-defined interest with keywords, URL patterns, and priority
- `CrawledPage` - Page data from crawling
- `IndexedPage` - Page data in the search index
- `SearchResult` - Search result with relevance score

### `personal_index.interests`

Interest management system.

**Key Classes:**
- `InterestStore` - Persistent storage for interests

### `personal_index.tags`

Tag management system.

**Key Classes:**
- `TagStore` - Persistent storage for tags

### `personal_index.content_filter`

Content filtering based on interests.

**Key Classes:**
- `ContentFilter` - Filter pages based on criteria
- `FilterConfig` - Configuration for filtering

### `personal_index.content_scoring`

Content scoring system.

**Key Classes:**
- `ContentScorer` - Score pages by relevance
- `ScoreWeights` - Configure scoring weights
- `ContentScore` - Score result with multiple factors

### `personal_index.index`

Search index management.

**Key Classes:**
- `SearchIndex` - Full-text search index
- `IndexedPage` - Page data in the index
- `SearchResult` - Search result

### `personal_index.pipeline_runner`

Pipeline orchestration.

**Key Classes:**
- `PipelineRunner` - Run the full pipeline
- `PipelineStats` - Pipeline execution statistics

## CLI Modules

### `personal_index.cli`

Main CLI entry point.

**Commands:**
- `main` - Main CLI group
- `init` - Initialize project
- `interests` - Interest management
- `tags` - Tag management
- `pipeline` - Run pipeline
- `search` - Search content
- `export` - Export results

### `personal_index.cli_pipeline`

Pipeline CLI commands.

**Commands:**
- `pipeline` - Run the full pipeline

### `personal_index.cli_search`

Search CLI commands.

**Commands:**
- `search` - Search indexed content
