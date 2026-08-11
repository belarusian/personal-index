# Changelog

All notable changes to personal-index will be documented in this file.

## [Unreleased]

### Added
- Comprehensive documentation suite (README, USAGE_GUIDE, ARCHITECTURE, CLI_REFERENCE)
- Full end-to-end pipeline integration tests
- Export functions for markdown, JSON, and CSV formats

### Changed
- Improved CLI command structure with proper subcommands
- Better error handling in pipeline execution

## [0.1.0] - 2024

### Added
- Initial release of personal-index
- Full-text search functionality
- Interest-based content filtering
- Web crawler with depth control and politeness
- Content extraction from HTML
- Scoring system for relevance ranking
- Auto-tagging based on interests
- Import/export functionality
- CLI with all core commands

### Features
- `personal-index init`: Initialize project
- `personal-index crawl <URL>`: Crawl web pages
- `personal-index pipeline <URL>`: Run full processing pipeline
- `personal-index search <QUERY>`: Search indexed content
- `personal-index interests add/list/remove`: Manage interests
- `personal-index tags add/list`: Manage tags
- `personal-index import <FILE>`: Import local files
- `personal-index export --format FORMAT`: Export results
- `personal-index status`: View index statistics

## Pipeline Stages

### Crawl
- Depth-limited crawling
- Politeness delays between requests
- Robots.txt compliance
- Interest-aware filtering

### Extract
- HTML parsing and content extraction
- Title, headings, and metadata extraction
- Link discovery for further crawling

### Filter
- Interest-based filtering
- Minimum content length threshold
- Duplicate detection

### Score
- Keyword matching with priority weights
- Content quality factors
- Domain authority estimation

### Tag
- Interest-based tags
- URL pattern tags
- Content heuristics

### Index
- Full-text search with inverted index
- Relevance ranking
- Persistent storage

## Testing

All tests pass:
- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for full workflows
- CLI integration tests

Run tests: `pytest`
