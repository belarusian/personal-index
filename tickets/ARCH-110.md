# ARCH-110 — improve web search page (search.compsci.boutique)

- **Status:** OPEN
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** search.html, web search interface
- **Issue:** #1659 (ARCH-110)

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

## Acceptance criteria

- [ ] Search responds instantly as user types (debounced)
- [ ] Search history visible on page
- [ ] Matched terms highlighted in results
- [ ] City filter working
- [ ] URLs with ?q= parameter work
- [ ] Loading progress indicator shown

## Self-review checklist (architect)

- [x] Component + scope stated
- [x] Acceptance criteria present
- [x] Concrete, verifiable outcomes
- [x] No tests/** written by the architect