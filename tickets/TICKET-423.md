# TICKET-423: content_enricher.ContentEnricher.enrich blanket docstring

- File: personal_index/content_enricher.py
- Function: ContentEnricher.enrich (line 80)
- Symptom (class-b doc-drift): docstring is the blanket one-liner
  "Enrich content with computed metrics, keywords, sentiment, and complexity
  analysis." It does not enumerate the exact sub-components the body sets on
  the returned EnrichedContent: word_count (count_words), reading_time
  (read_time_minutes), keywords (extract_keywords top_n/min_freq=1), the
  `if html:` guard that sets has_code/has_links/has_images only when html is
  truthy (else left at the dataclass default False), sentiment_score
  (_compute_sentiment, [-1,1]), complexity_score (_compute_complexity, [0,1]),
  and that language is NEVER computed (stays at the dataclass default 'en').
- Evidence: line 81 `"""Enrich content with computed metrics, keywords,
  sentiment, and complexity analysis.` vs body lines 92-117 (word_count,
  reading_time, keywords, `if html:` block, sentiment, complexity, return).
- Minimal additive fix: reword the docstring to state the EXACT behavior
  (enumerate each field set + the html guard + the language-not-computed
  note), KEEPING the phrase "computed metrics, keywords, sentiment, and
  complexity" intact (pinned by the TICKET-340 regression test at
  tests/test_content_enricher.py:190/200) and NOT introducing "computed
  metadata". Add ONE pinning test asserting the returned EnrichedContent
  object fields for a normal case (html with code/links/images) AND the
  guard path (html=None -> has_code/has_links/has_images stay False,
  language stays 'en').
- Status: OPEN
- Issue: #684
