# Architecture

## System Overview

personal-index is a personal web search engine that scans, filters, and indexes the web based on user-defined interests.

## Core Components

### 1. Crawler (`personal_index.crawler`)

**Purpose:** Fetch web pages from URLs

**Key classes:**
- `Crawler` - Main crawler with depth control
- `CrawlerConfig` - Configuration for crawling behavior

**Features:**
- Configurable crawl depth
- Politeness delays between requests
- Rate limiting per domain
- Robots.txt compliance
- Domain filtering

### 2. Extractor (`personal_index.content_extractor`)

**Purpose:** Parse HTML and extract structured content

**Key classes:**
- `ContentExtractor` - Extracts text, headings, links, images
- `ExtractedContent` - Data class for extracted data

**Features:**
- Title extraction (including og:title)
- Meta tag extraction
- Heading extraction
- Link extraction
- Image extraction
- Text normalization

### 3. Filter (`personal_index.content_filter`)

**Purpose:** Remove unwanted pages

**Key classes:**
- `ContentFilter` - Main filter logic
- `FilterConfig` - Configuration for filtering rules

**Features:**
- Content length filtering
- Blocked domains
- Pattern matching
- Interest-based filtering
- Minimum relevance score

### 4. Scorer (`personal_index.content_scoring`)

**Purpose:** Rate pages by relevance

**Key classes:**
- `ContentScorer` - Calculates relevance scores
- `ScoreWeights` - Configurable scoring weights
- `ScoreResult` - Score breakdown

**Features:**
- Keyword matching with interests
- Word count scoring
- Domain authority proxy
- Configurable weightings

### 5. Tagger (`personal_index.content_tagger`)

**Purpose:** Auto-tag pages with keywords

**Key classes:**
- `TagStore` - Manages tags and page associations
- `Tag` - Tag data model

**Features:**
- Interest-based tagging
- Keyword extraction
- Per-page tag tracking
- Persistent storage

### 6. Index (`personal_index.index`)

**Purpose:** Full-text search index

**Key classes:**
- `SearchIndex` - Main index with JSON persistence
- `IndexedPage` - Indexed page data model
- `SearchResult` - Search result data model

**Features:**
- Full-text search
- Tokenization with stop words
- Inverted index
- Relevance scoring
- Persistent storage

### 7. Interest Store (`personal_index.interests`)

**Purpose:** User-defined interests for scoring

**Key classes:**
- `InterestStore` - Manages user interests
- `Interest` - Interest data model

**Features:**
- Interest with keywords and URL patterns
- Pattern matching
- Scoring based on matches
- Persistent storage

### 8. Pipeline Orchestrator (`personal_index.pipeline_orchestrator`)

**Purpose:** Coordinates all pipeline stages

**Key classes:**
- `PipelineOrchestrator` - Main orchestrator
- `PipelineResult` - Result data class

**Features:**
- End-to-end pipeline execution
- Progress callbacks
- Error handling
- Resource management

## Data Flow
