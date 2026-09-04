# TICKET-348: content_filter._matches_interests docstring over-promises (class b)

Status: RESOLVED (merged to main 0c97dfc, gh #535 merged, gh #534 closed)
Module: personal_index/content_filter.py
Method: ContentFilter._matches_interests (line ~113)

## Symptom
The docstring says only "Check if page matches any interests." — a blanket
"check" claim. The body actually performs more than a pure check:
1. Returns True immediately when self.interest_store is None (no check at all).
2. Builds text = f"{page.title} {page.content}" and calls
   interest_store.matches_any(text, page.url).
3. On a match, MUTATES the page: sets page.matched_interests to the list of
   matched interest names and page.relevance_score to
   interest_store.total_score(text) — a hidden side effect the docstring never
   mentions.
4. Returns True on a match, False when no interest matches.

The blanket "check" hides both the no-store short-circuit and the two field
mutations.

## Evidence
personal_index/content_filter.py lines 113-123:
    def _matches_interests(self, page: CrawledPage) -> bool:
        """Check if page matches any interests."""
        if not self.interest_store:
            return True
        text = f"{page.title} {page.content}"
        matches = self.interest_store.matches_any(text, page.url)
        if matches:
            page.matched_interests = [m.name for m in matches]
            page.relevance_score = self.interest_store.total_score(text)
            return True
        return False

## Minimal additive fix (doc-only, no behavior change)
Reword the docstring to state the exact conditional: no-store short-circuit
returns True; otherwise checks whether any interest matches the combined
"title + ' ' + content" text (and url); on a match sets page.matched_interests
to the matched interest names and page.relevance_score to the store's
total_score of that text, then returns True; returns False when no interest
matches. Add ONE behavior test pinning the corrected claim against the returned
object: a matching page gets page.matched_interests populated with the matched
interest name and page.relevance_score set to the store's total_score, and the
method returns True; a non-matching page returns False and leaves the fields
untouched.

Issue: #534
