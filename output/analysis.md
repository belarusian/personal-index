# Analysis: Content Categorizer Module

## Existing Codebase Context

The personal-index project is a personal web search engine with modules for:
- **Content extraction** (`content.py`, `content_extractor.py`) — extracts text, headings, meta from HTML
- **Keyword extraction** (`keyword_extractor.py`) — frequency-based keyword extraction with scoring
- **Text utilities** (`text_utils.py`) — tokenization, stopwords, slugify, truncate, etc.
- **Tags** (`tags.py`) — manual tagging system with persistence
- **URL classification** (`url_classifier.py`) — classifies URLs by type (API, media, document, etc.)
- **Interests** (`interests.py`) — user-defined interests with keywords, topics, URL patterns
- **Content scoring** (`content_scoring.py`) — multi-factor quality scoring
- **TF-IDF** (`tfidf.py`) — term frequency-inverse document frequency

## What's Needed: Content Categorizer

A module that **automatically classifies saved items by topic** based on their content. This bridges the gap between:
1. Raw extracted content (text, keywords, headings)
2. Manual tags (user-assigned)
3. URL-level classification (format-based, not topic-based)

## Design Approach

The `content_categorizer.py` module will:

1. **Define a set of topic categories** with associated keywords/signals (e.g., "technology", "science", "health", "finance", etc.)
2. **Analyze content** using multiple signals:
   - Keyword matching against topic dictionaries
   - Title/heading analysis
   - URL path hints
   - Meta description analysis
3. **Produce a `CategorizationResult`** with:
   - Primary topic (highest confidence)
   - Secondary topics (with confidence scores)
   - Reasons for classification
4. **Support custom topic definitions** so users can add their own categories
5. **Support batch categorization** for efficiency

## Code Patterns to Follow

- Dataclasses for data structures (matching `tags.py`, `keyword_extractor.py`)
- Class-based API with clear public methods (matching `URLClassifier`, `ContentScorer`)
- Type hints throughout
- No external ML dependencies — rule-based keyword matching
- Tests following existing patterns (pytest, `setup_method`, descriptive test names)

## Files to Create

1. `personal_index/content_categorizer.py` — main module
2. `tests/test_content_categorizer.py` — comprehensive tests
