# personal-index

A personal web search engine that scans, filters, and indexes the web based on your interests.

## Overview

personal-index is a Python-based tool that lets you define topics and keywords you care about, then automatically crawls the web to find, filter, and index relevant content. It provides a local search index with relevance scoring, scheduled crawling, and a comprehensive CLI for managing your personal knowledge base.

### Key Features

- **Interest-based crawling**: Define interests with keywords, URL patterns, and topics. The crawler only indexes pages that match your interests.
- **Full-text search**: Local search index with TF-IDF relevance scoring and snippet generation.
- **Scheduled crawling**: Set up periodic crawl jobs that run on configurable intervals.
- **Content extraction**: Extracts titles, text, meta descriptions, headings, links, and images from HTML pages.
- **Content filtering**: Filter pages by content length, blocked domains, regex patterns, and interest matching.
- **REST & GraphQL APIs**: Optional FastAPI-based REST endpoints and GraphQL schema for programmatic access.
- **API authentication**: Token-based auth with HMAC signatures, RBAC (Role-Based Access Control), and middleware.
- **API documentation**: Auto-generated OpenAPI specs, Markdown docs, and Swagger UI.
- **Rate limiting**: Multiple rate-limiting strategies (fixed window, sliding window, token bucket).
- **Content analytics**: Engagement scoring, categorization, trend analysis, and dashboard widgets.
- **Content metrics**: Word counts, reading time estimates, readability scores, and statistical summaries.
- **Content versioning**: Version control for saved content with diff, rollback, and changelog capabilities.
- **Content security**: CSP policy builder, XSS sanitization, security headers, input validation, and security audit scanning.
- **GDPR compliance**: Compliance checking, DSAR handling, data erasure, portability, and retention policies.
- **Privacy tools**: IP anonymization, data classification, privacy policies, and consent management.
- **Export formats**: PDF, CSV, JSON, and Markdown export with configurable layouts and pagination.
- **Content reporting**: Multi-section reports with filters, metadata, and formatted output.
- **Dashboard**: Widget-based dashboard with stats aggregation and rendering.
- **Audit logging**: Audit entries, filtering, reporting, and anomaly detection.
- **Backup & verification**: Backup creation with manifest, integrity checks, and reporting.
- **NLP tools**: Text processing, keyword extraction, sentiment analysis, and summarization.
- **CLI interface**: Full-featured CLI with Click for managing interests, crawling, searching, and scheduling.

## Installation

### Prerequisites

- Python >= 3.10

### Install from source
