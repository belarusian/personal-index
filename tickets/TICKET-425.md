# TICKET-425 (RESOLVED)

- file: personal_index/content_annotations.py
- function: AnnotationManager.add
- symptom: class-(b) doc-drift. The docstring is a blanket one-liner
  ("Add an annotation.") that does not enumerate the sub-components the
  body actually performs.
- evidence: line 108-109 `def add(self, annotation: Annotation) -> None:`
  with docstring `"""Add an annotation."""`; the body (lines 110-129)
  maintains FIVE indexes:
    1. _annotations[annotation_id] = annotation (always)
    2. _by_content[content_id] list append (always)
    3. _by_author[author] list append (ONLY when annotation.author is truthy)
    4. _by_type[annotation_type.value] list append (always)
    5. _by_tag[tag] list append (for each tag in annotation.tags)
- minimal additive fix: reword the docstring to enumerate the five index
  updates with the exact guard (author truthy) and the type-key
  (annotation_type.value); add ONE pinning test asserting the RETURNED /
  observable index state for the normal case (author + tags present) AND
  the guard path (falsy author -> _by_author untouched).
- Issue: #688
