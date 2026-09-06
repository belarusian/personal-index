# TICKET-463

- Status: RESOLVED (PR #768, merge 24d1505)
- Module: personal_index/tags.py
- Class: (b) doc-drift (blanket-adjective docstring where the body applies a NAMED predicate)

## Symptom
`TagStore.get_tags_for_page(url)` docstring is the blanket claim
"Get all tags for a page." The body actually applies a named predicate:
`return [self._tags[name] for name in tag_names if name in self._tags]`
— it returns only the tags whose name still exists in the tag registry
(`self._tags`), silently dropping any dangling tag name that is present in
`self._page_tags[url]` but no longer in `self._tags`.

## Evidence
- personal_index/tags.py: `def get_tags_for_page` docstring "Get all tags for a page."
- body: `tag_names = self._page_tags.get(url, set())` then
  `return [self._tags[name] for name in tag_names if name in self._tags]`
  (the `if name in self._tags` filter is the named predicate the docstring omits).

## Minimal additive fix
1. Reword the docstring to state the exact predicate: returns the Tag objects
   for the page whose tag names still exist in the registry; dangling names
   (present on the page but no longer registered) are dropped.
2. Add ONE behavior test pinning the corrected claim:
   - normal case: a page with two registered tags returns both;
   - guard path: a page whose `_page_tags` entry contains a dangling (unregistered)
     name returns only the registered tags (dangling name dropped).

## Issue
Issue: #767
