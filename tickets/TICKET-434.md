# TICKET-434: AnnotationManager.get_stats docstring over-promise (class-(b))

- File: personal_index/content_annotations.py
- Function: AnnotationManager.get_stats (line ~264)
- Symptom: docstring is a blanket "Get annotation statistics." that does not
  enumerate the returned dict's keys or their semantics.
- Evidence: line 265 `"""Get annotation statistics."""`; body returns a dict
  with exactly three keys:
    - "total": len(self._annotations)
    - "by_content": len(self._by_content)  (number of distinct content ids, NOT total annotations)
    - "by_type": {annotation_type.value: count}  (per-type counts)
  The "by_content" key is a distinct-content-id count, which a blanket
  "statistics" docstring does not convey.
- Minimal additive fix: reword the docstring to enumerate the three returned
  keys and their exact semantics (total = annotation count; by_content =
  distinct content-id count; by_type = per-type count dict), and add ONE
  pinning test asserting the returned dict fields for the normal case AND the
  empty-manager guard path (total 0 / by_content 0 / by_type {}).
- Issue: #706
- Status: RESOLVED (306f08b, PR #707)
