# TICKET-410: process_content docstring over-promise (class b)

- File: personal_index/app.py
- Function: PersonalIndexApp.process_content (line ~249)
- Symptom: blanket docstring "Process content through the full pipeline."
  does not enumerate the sub-steps, the fields the pipeline adds to the
  returned dict, the passes_filter guard, or the search-index side effect.
- Evidence: line 250 `"""Process content through the full pipeline."""`
- Minimal additive fix: reword to the EXACT behavior:
  (1) initialize() (idempotent);
  (2) build data dict {url, title, raw_content};
  (3) pipeline.run(data) runs extract->filter->score->tag (all on_error="continue"),
      adding extracted_text, title (fallback "Untitled"), passes_filter, score, tags;
  (4) GUARD: only when result.get("passes_filter", True) is truthy is the item
      added to search_index (id=url, url, title default "Untitled",
      content=extracted_text, score, tags);
  (5) returns the result dict.
  Add ONE pinning test asserting the RETURNED dict fields (normal case) AND the
  guard path (passes_filter False -> not added to search index).
- Status: OPEN
- Issue: #658
