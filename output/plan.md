# Implementation Plan: Content Categorizer

## Batch 1: Core data structures and topic definitions
- Create `TopicCategory` dataclass (name, keywords, description, weight)
- Create `CategorizationResult` dataclass (primary_topic, topics with scores, confidence, reasons)
- Define built-in topic dictionaries (technology, science, health, finance, etc.)
- Commit: "feat: add content_categorizer module with topic definitions and data structures"

## Batch 2: Categorization engine
- Create `ContentCategorizer` class with:
  - `categorize(text, title="", url="", meta_description="")` method
  - Keyword matching against topic dictionaries
  - Title/heading boosting
  - URL path hint analysis
  - Confidence scoring
  - Support for custom topics
- Commit: "feat: implement content categorization engine with multi-signal analysis"

## Batch 3: Tests
- Test data structures
- Test categorization with known content samples
- Test edge cases (empty text, no match, multiple topics)
- Test custom topic addition
- Test batch categorization
- Test URL hint analysis
- Commit: "test: add comprehensive tests for content_categorizer module"
