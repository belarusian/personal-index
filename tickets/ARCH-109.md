# ARCH-109 — build and share a multi-city search index (15 cities across 4 continents)

- **Status:** OPEN
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** .personal_index/ (index data) + indexing pipeline
- **Issue:** #1657 (ARCH-109)

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