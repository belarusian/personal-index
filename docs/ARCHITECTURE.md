# Architecture

## System Overview

personal-index is a personal web search engine that scans, filters, and indexes the web based on user-defined interests.

## Core Components

### 1. Crawler (`personal_index.crawler`)

Responsible for fetching web pages:
- **Depth-limited crawling**: Follow links up to N levels deep
- **Politeness**: Delay between requests, respect robots.txt
- **Interest-aware**: Skip pages that don't match interests
- **Rate limiting**: Control request frequency

### 2. Content Extractor (`personal_index.content_extractor`)

Parses HTML and extracts structured content:
- Title extraction
- Main content extraction (removes navigation, ads)
- Metadata extraction (description, keywords)
- Link extraction for further crawling

### 3. Filter (`personal_index.content_filter`)

Decides which pages to keep:
- **Interest matching**: Does content match user interests?
- **Quality thresholds**: Minimum content length
- **Duplicate detection**: Avoid indexing same content twice

### 4. Scorer (`personal_index.content_scoring`)

Calculates relevance scores (0-1):
- Keyword match count
- Interest priority weights
- Content quality factors
- Domain authority estimates

### 5. Tagger (`personal_index.tags`)

Auto-generates tags:
- Interest-based tags
- URL pattern tags
- Content heuristics (blog, api, docs)
- User-defined tags

### 6. Search Index (`personal_index.index`)

Full-text search with:
- Inverted index for fast searching
- Stop word filtering
- Tokenization and normalization
- Relevance ranking

## Data Flow
