# Module Documentation

This document provides per-module documentation for all components in personal-index.

---

## Core Modules

### `personal_index.models`

Core data models for the entire system.

**Classes:**

- `InterestType` — Enum: `KEYWORD`, `TOPIC`, `URL_PATTERN`
- `Interest` — User-defined interest with keyword/URL/topic matching and relevance scoring
- `CrawlConfig` — Crawler configuration (depth, delay, rate limits, domains)
- `CrawledPage` — A fetched page with extracted content and metadata
- `IndexedPage` — A page stored in the search index
- `SearchResult` — A search result with score and snippet
- `Page` — A page model with UUID-based ID for the search index

All models support `to_dict()` / `from_dict()` serialization.

### `personal_index.interest_store`

Persistent JSON-based interest storage.

**Classes:**

- `InterestStore(storage_path: str)` — CRUD operations for interests with file persistence

**Key methods:**

- `add(interest)` — Add an interest
- `remove(name)` — Remove by name
- `get(name)` — Retrieve by name
- `list_all(enabled_only=False)` — List all or enabled-only
- `toggle(name)` — Flip enabled status
- `update_priority(name, priority)` — Update priority (clamped 1–10)
- `matches_any(text, url)` — Find interests matching text/URL
- `total_score(text)` — Aggregate relevance score across all interests

### `personal_index.pipeline`

Generic sequential content processing pipeline.

**Classes:**

- `PipelineStep(name, handler, enabled=True, on_error="continue")` — A single pipeline step
- `PipelineResult(success, data, steps_executed, steps_failed, errors)` — Pipeline execution result
- `ContentPipeline(name="default")` — The pipeline orchestrator

**Usage:**
