# Pipeline Workflow

This document explains how personal-index processes content through its pipeline.

## Overview

The pipeline transforms raw web content into a searchable, tagged index:

**crawl → extract → filter → score → tag → index → search**

## Detailed Pipeline Stages

### 1. Crawl Stage

**Purpose**: Fetch or read content

**Inputs**: URLs or file paths

**Process**:
- For URLs: HTTP GET request with politeness delays
- Respects robots.txt and rate limits
- Follows links up to configured depth
- For files: Reads from local filesystem

**Output**: Raw HTML/text content

### 2. Extract Stage

**Purpose**: Parse and extract meaningful content

**Inputs**: Raw HTML/text

**Process**:
- Parse HTML with BeautifulSoup
- Extract title, meta description
- Get text content (paragraphs, headings)
- Remove scripts and styles
- Count words and extract links/images

**Output**: Structured page object with title, content, metadata

### 3. Filter Stage

**Purpose**: Remove unwanted content

**Inputs**: Page object

**Process**:
- Check minimum content length
- Check maximum content length
- Verify title is present
- Check against blocked domains
- Match required patterns (optional)
- Interest matching (optional)

**Output**: Pass/fail decision with reasons

### 4. Score Stage

**Purpose**: Calculate relevance score

**Inputs**: Page object, interests

**Process**:
- Count keyword matches in content
- Calculate quality score (word count, structure)
- Check domain authority
- Apply interest weights
- Combine into final score

**Output**: Relevance score (0.0 - 1.0)

### 5. Tag Stage

**Purpose**: Add metadata tags

**Inputs**: Page object, interests

**Process**:
- Match interests to content
- Extract keywords from content
- Apply interest-based tags
- Store tags in tag store

**Output**: List of tags for the page

### 6. Index Stage

**Purpose**: Add to search index

**Inputs**: Page object with tags

**Process**:
- Tokenize content (lowercase, remove stop words)
- Build word-to-page index
- Calculate TF-IDF scores
- Store in JSON file

**Output**: Indexed page ready for search

### 7. Search Stage

**Purpose**: Query the index

**Inputs**: Search query

**Process**:
- Tokenize query
- Look up matching pages
- Rank by relevance score
- Generate snippets
- Return results with tags

**Output**: List of search results

## Pipeline Configuration
