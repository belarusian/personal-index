# TICKET-12-3: Refactor `rss.RSSParser._parse_atom_entry` (57L, line 191)

## What's wrong

`RSSParser._parse_atom_entry` in `personal_index/rss.py` (line 191) is 57 lines and parses 9 fields from an Atom XML entry. Each field follows the identical pattern:
1. Try namespaced find (`atom:field`)
2. Fallback to non-namespaced find (`field`)
3. Extract text with null-safety guard

This pattern repeats 8 times (title, link, summary, content, author, published, updated, id), producing ~6 lines of near-identical code per field.

## Evidence
