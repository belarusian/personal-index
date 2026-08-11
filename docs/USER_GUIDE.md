# Personal Index User Guide

## Overview

Personal Index is a personal web content management toolkit that crawls, filters, scores, tags, and indexes web content based on your interests. It provides a local search engine for content you care about.

## Quick Start

```bash
# Install
pip install personal-index

# Initialize
personal-index init

# Add your interests
personal-index interests add -n programming -k python -k javascript -k rust

# Import local files
personal-index pipeline --import-file ./articles/ --recursive

# Or crawl a website
personal-index pipeline https://example.com

# Search your index
personal-index search "python tutorials"

# Export results
personal-index export --format markdown
```

## Core Concepts

### The Pipeline

Personal Index processes content through a 6-stage pipeline:

1. **Crawl** - Fetch content from URLs or read local files
2. **Extract** - Parse and extract readable text from HTML, Markdown, etc.
3. **Filter** - Remove content that does not meet quality thresholds
4. **Score** - Rank content based on your interests and quality signals
5. **Tag** - Auto-tag content based on detected topics and interests
6. **Index** - Build a searchable index of all processed content

### Interests

Interests define what content matters to you. Pages matching your interests get higher scores:

```bash
# Add an interest with keywords
personal-index interests add -n machine-learning -k "neural networks" -k "deep learning"

# List all interests
personal-index interests list

# Remove an interest
personal-index interests remove machine-learning
```

### Tags

Tags are manual labels you can apply to indexed content:

```bash
# Add a tag to a URL
personal-index tags add important https://example.com/article

# List all tags
personal-index tags list

# Remove a tag
personal-index tags remove important https://example.com/article
```

## Commands Reference

### personal-index init

Initialize a new personal-index project. Creates the data directory and default configuration.

### personal-index pipeline

Run the full content pipeline. Supports both URL crawling and local file import.

Options:
- `--import-file, -i` - Import local files instead of crawling
- `--depth, -d` - Max crawl depth (default: 3)
- `--max-pages, -m` - Max pages to crawl (default: 100)
- `--min-score` - Minimum score threshold (default: 0.0)
- `--min-content-length, -l` - Minimum content length (default: 10)
- `--recursive, -r` - Recursively import directories
- `--data-dir` - Data directory path

### personal-index search

Search your indexed content.

### personal-index crawl

Crawl web pages without running the full pipeline.

### personal-index extract

Extract content from URLs or files.

### personal-index score

Re-score indexed content based on current interests.

### personal-index export

Export indexed content in JSON, Markdown, or CSV format.

### personal-index list

List all indexed pages.

### personal-index stats

Show index statistics including page count, interests, and tags.

### personal-index status

Show system status and health information.

### personal-index doctor

Diagnose issues with your personal-index setup.

### personal-index clear

Clear all indexed content.

### personal-index remove

Remove a specific page from the index by URL.

### personal-index top

Show the highest-scored indexed pages.

### personal-index verify

Verify index integrity and data consistency.

### personal-index watch

Watch a directory for changes and re-index automatically.

### personal-index schedule

Manage scheduled crawl jobs (add, list, remove, run).

## Configuration

Personal Index uses config.yaml for configuration:

```yaml
crawler:
  max_depth: 3
  max_pages: 100
  timeout: 30
  delay: 1.0

filter:
  min_content_length: 100
  require_interest_match: false

scoring:
  min_score_threshold: 0.0

scheduler:
  interval_hours: 24
```

## Data Directory

By default, data is stored in .personal_index/:

```
.personal_index/
  cache/           Cached crawl results
  archive/         Archived content
  backups/         Index backups
  search_index.json   Search index
  interests.json      User interests
  tags.json           Content tags
  schedules.json      Scheduled jobs
```

## Common Workflows

### Local Content Indexing

```bash
personal-index init
personal-index interests add -n tech -k python -k rust -k go
personal-index pipeline --import-file ./tech-articles/ --recursive
personal-index search "python async"
personal-index export --format markdown
```

### Web Content Monitoring

```bash
personal-index init
personal-index interests add -n news -k "artificial intelligence" -k technology
personal-index schedule add -n daily-news https://techcrunch.com
personal-index schedule run daily-news
personal-index top --limit 10
```

### Research Collection

```bash
personal-index init
personal-index interests add -n research -k "machine learning" -k NLP
personal-index pipeline --import-file ./papers/ --recursive
personal-index search "transformer architecture"
personal-index tags add important https://arxiv.org/abs/1706.03762
personal-index export --format json
```

## Troubleshooting

### No results from search

1. Run `personal-index doctor` to check your setup
2. Verify content was indexed: `personal-index stats`
3. Check if interests are configured: `personal-index interests list`

### Pipeline errors

1. Check the error output from the pipeline command
2. Verify file paths are correct
3. Ensure files have sufficient content (default minimum: 10 chars)

### Slow crawling

1. Reduce `--max-pages` to limit crawl scope
2. Increase `--delay` between requests
3. Use `--import-file` for local content instead of crawling
