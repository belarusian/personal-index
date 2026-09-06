# TICKET-503: URLClassifier.classify docstring is a one-liner that omits the exact contract

Status: OPEN
Issue: #850
Module: personal_index/url_classifier.py
Function: classify
Class: (b) docstring drift (under-specification)

## Symptom
`URLClassifier.classify` docstring is a single line: "Classify a URL into a
category." It does not state:
- that the URL is preserved as-is in the result
- that matching is case-insensitive (path and full URL are lowercased)
- the fixed pattern-check order (REDIRECT, FEED, API, STATIC, MEDIA, DOCUMENT)
- the confidence value per category
- the default PAGE fallback (confidence 0.5)
- that reasons is a single-element list
- that the method never returns None

## Evidence (line)
- Original docstring: personal_index/url_classifier.py:138
  ("""Classify a URL into a category.""")
- Body: urlparse(url); path = parsed.path.lower(); full_url = url.lower();
  patterns checked in fixed order; default PAGE 0.5.

## Minimal additive fix
Reword the docstring to state the EXACT contract (preserved URL, case-insensitive
matching, fixed pattern order, per-category confidence, default PAGE 0.5,
single-element reasons list, never None). Add pinning behavior tests that pin
the corrected claims against the returned ClassificationResult, including the
guard path (empty/falsy URL) alongside normal cases.
