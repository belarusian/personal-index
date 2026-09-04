# TICKET-344: content_merger._merge_unique_paragraphs docstring over-promises "unique paragraphs"

- File: personal_index/content_merger.py
- Function: ContentMerger._merge_unique_paragraphs (line ~158)
- Symptom: docstring says "Merge unique paragraphs from all sources" (blanket "unique"),
  but the body dedupes on a case-insensitive, whitespace-stripped normalized form
  (`normalized = para.strip().lower()`). Two paragraphs differing only in case or
  surrounding whitespace are treated as the same and collapse to one.
- Evidence line: `normalized = para.strip().lower()` then `if normalized and normalized not in seen_paragraphs:`
- Minimal additive fix: reword docstring to state the exact dedup key (case-insensitive,
  whitespace-stripped paragraph text), and add ONE behavior test pinning that two
  paragraphs differing only in case/whitespace merge to a single paragraph.
- Status: OPEN
- Issue: #526
