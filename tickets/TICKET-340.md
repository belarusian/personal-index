# TICKET-340: content_enricher docstring over-promises "computed metadata" (language never computed)

Status: RESOLVED

## File
personal_index/content_enricher.py

## Symptom
The `ContentEnricher` class docstring (line 52) says "Enrich content with
computed metadata and analysis." and the `enrich` method docstring (line 80)
says "Enrich content with computed metadata." Both claim the metadata is
computed. However, the `language` field of `EnrichedContent` is NEVER computed
by `enrich` — it is only ever its dataclass default `"en"` (assigned at line 26
default, read at line 42 in `to_dict`). The body computes word_count,
reading_time, keywords, has_code/has_links/has_images, sentiment_score and
complexity_score, but not language. So "computed metadata" over-promises: one
of the returned metadata fields is a static default, not a computed value.

## Evidence
- line 26: `language: str = "en"` (default only)
- line 42: `"language": self.language,` (read in to_dict)
- no `enriched.language = ...` assignment anywhere in the module
- line 52: `"""Enrich content with computed metadata and analysis."""`
- line 80: `"""Enrich content with computed metadata.`

## Minimal additive fix
Reword the two docstrings so they do not claim `language` is computed. Change
"computed metadata" to a precise enumeration of what IS computed:
"computed metrics, keywords, sentiment, and complexity analysis". No behavior
change. Add a regression test asserting the corrected wording (inspect.getsource
pattern, mirroring TICKET-339) and that behavior is unchanged (language stays
"en" after enrich).

## Issue
Issue: #518
