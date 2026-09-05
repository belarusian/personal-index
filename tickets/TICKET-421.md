# TICKET-421

- Status: OPEN
- File: personal_index/content_merger.py
- Function: ContentMerger.merge (line 72)
- Symptom: class-(b) doc-drift. Docstring is the blanket "Merge multiple
  content sources." It does not enumerate the guard path (returns None when
  sources is empty), the strategy dispatch (longest / highest_priority /
  unique_paragraphs, else concatenate default), the priority-descending sort,
  or the returned MergedContent fields (url/title/content/tags/metadata/
  source_count/sources/merge_strategy).
- Evidence: line 73 `"""Merge multiple content sources.`
- Minimal additive fix: reword the docstring to state the EXACT behavior
  (enumerate the empty-sources guard -> None, the four strategy branches, the
  priority-descending sort, and the returned MergedContent fields), and add
  ONE pinning test asserting the returned MergedContent object fields for a
  normal concatenate case (url/title/content/tags/source_count/sources/
  merge_strategy) AND the empty-sources guard path (merge([]) is None).
- Issue: #680
