# Personal Index

A personal web search engine that crawls, filters, scores, and indexes content based on your interests.

## Features

- **Crawl**: Discover and fetch web pages from seed URLs
- **Extract**: Parse HTML to extract meaningful text content
- **Filter**: Remove low-quality or irrelevant pages
- **Score**: Rank content by relevance to your interests
- **Tag**: Auto-tag pages based on matched interests
- **Index**: Build a fast full-text search index
- **Search**: Query your personal index with natural language

## Installation

pip install -e .

## Quick Start

personal-index init
personal-index interests add -n Python -k python
personal-index pipeline https://example.com
personal-index search python
personal-index status

## Commands

- **init** - Initialize a new project
- **interests** - Manage tracked interests (add/list/remove/toggle)
- **pipeline <urls>** - Run crawl -> extract -> filter -> score -> tag -> index
- **search <query>** - Search indexed content
- **import <path>** - Import local files into the index
- **export** - Export indexed content (markdown/json/csv)
- **tag** - Manage content tags (list/add/remove)
- **status** - Show system status
- **config** - Manage configuration

## Configuration

Copy config.sample.yaml to config.yaml and customize.

## Architecture

Crawl -> Extract -> Filter -> Score -> Tag -> Index -> Search

## License

MIT
