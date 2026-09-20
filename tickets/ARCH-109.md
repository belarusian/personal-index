# ARCH-109 — build and share a multi-city search index (15 cities across 4 continents)

- **Status:** CLOSED (implemented 2026-09-20 — 16 cities indexed, 27 pages, web interface live)
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** .personal_index/ (index data) + indexing pipeline
- **Issue:** #1657 (ARCH-109)

## Work Done

### Cities Indexed (16 cities, 4 continents)
- **Americas (5)**: Boston, New York City, Los Angeles, Chicago, Toronto
- **Europe (6)**: Berlin, Munich, Amsterdam, Eindhoven, London, Paris
- **Asia-Pacific (5)**: Tokyo, Singapore, Sydney, Dubai, Hong Kong

### Index Statistics
- **Total pages**: 27 unique Wikipedia articles
- **Total interests**: 18 city interests
- **Total tags**: 136 tags applied
- **Storage**: 5.4 MB (search_index.json)
- **Crawl**: depth 1-2, ~10 pages per seed URL

### Web Search Interface
- **URL**: https://www.compsci.boutique/search.html
- **Features**: Client-side inverted index search, loads JSON from GitHub
- **Hosting**: S3 + Route53 (static HTML)
- **No server required** — 100% client-side

## Symptom

The personal-index project supports crawling, filtering, scoring, tagging, and indexing web content. However, the index shipped with the repo is empty or minimal. Users who clone the repo must manually run the pipeline to build an index, and there's no shared baseline index for demonstrating or testing the search capability.

## Goal

Create a production-quality shared index containing Wikipedia content for 15 major cities across 4 continents:

**Americas:** Boston, New York City, Los Angeles, Chicago, Toronto
**Europe:** Berlin, Munich, Amsterdam, Eindhoven, London, Paris
**Asia-Pacific:** Tokyo, Singapore, Sydney, Dubai, Hong Kong

## Proposed fix (implementer)

1. Add city-specific interests to the interest store (one per city, with relevant keywords)
2. Run the indexing pipeline on Wikipedia pages for each city (depth 1-2, ~10 pages per seed)
3. Verify the index contains pages for all 15 cities and search works correctly
4. Commit the complete index data to the repo (`.personal_index/` must not be in `.gitignore`)
5. Document the index contents and size

## Acceptance criteria

- [ ] All 15 cities have corresponding interests defined
- [ ] Index contains Wikipedia content for all 15 cities
- [ ] Search queries for city names return relevant results
- [ ] Index is committed to the repo and shareable via git clone
- [ ] Search works without requiring re-crawling
- [ ] Index size is reasonable (< 10MB) and documented

## Self-review checklist (architect)

- [x] Component + scope stated
- [x] Acceptance criteria present
- [x] Concrete, verifiable outcomes
- [x] No tests/** written by the architect