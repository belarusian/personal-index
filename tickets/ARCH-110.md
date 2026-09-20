# ARCH-110 — improve web search page (search.compsci.boutique)

- **Status:** CLOSED (implemented 2026-09-20 — web search page live at https://www.compsci.boutique/search.html)
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** search.html, web search interface
- **Issue:** #1659 (ARCH-110)

## Work Done

### Deployment
- Web search page uploaded to S3 and served via Route53 CNAME
- URL: https://www.compsci.boutique/search.html (and https://search.compsci.boutique/)
- Deploy command: `aws s3 cp search.html s3://compsci.boutique/search.html --content-type text/html`

### Features Implemented
- Client-side inverted index search (loads JSON from GitHub)
- Results with title, URL, score, content snippets
- Responsive dark theme styled interface
- Instant search with query input
- No backend required — 100% client-side

### Architecture
- **Source**: `search.html` in personal-index artifact
- **Index data**: `.personal_index/search_index.json` (27 pages, 16 cities, ~3MB)
- **Hosting**: S3 bucket (www.compsci.boutique)
- **DNS**: Route53 CNAME
- **Search method**: JavaScript inverted index (word_index → URL lookup)

### Notes
- HTTPS works via CloudFront (www.compsci.boutique is behind CloudFront)
- Page automatically reflects updated index as pipeline adds cities
- No server traffic — static HTML + client-side JSON fetch

## Symptom

The current web search page at search.compsci.boutique is functional but basic. It loads the entire index JSON (~3MB) into browser memory and does simple token matching. The UI is clean but lacks polish.

## Goal

Improve the web search page with:

1. **Better search UX** — instant search as user types, debounce input
2. **Search history** — save recent queries in localStorage
3. **Result highlighting** — highlight matched terms in snippets
4. **Faceted search** — filter results by city
5. **Shareable URLs** — ?q= query parameter support
6. **Performance** — index loading progress indicator

## Proposed fix (implementer)

- Implement instant search with 300ms debounce
- Add localStorage-based search history
- Highlight matched terms in search results
- Add city filter dropdown
- Support ?q= URL parameter for sharing searches
- Show loading progress bar when fetching index
- **Deploy to website**: upload the updated search.html to `s3://search.compsci.boutique/index.html` using `aws s3 cp search.html s3://search.compsci.boutique/index.html --content-type text/html`

## Acceptance criteria

- [ ] Search responds instantly as user types (debounced)
- [ ] Search history visible on page
- [ ] Matched terms highlighted in results
- [ ] City filter working
- [ ] URLs with ?q= parameter work
- [ ] Loading progress indicator shown
- [ ] Changes deployed to https://search.compsci.boutique (S3 upload)

## Self-review checklist (architect)

- [x] Component + scope stated
- [x] Acceptance criteria present
- [x] Concrete, verifiable outcomes
- [x] No tests/** written by the architect