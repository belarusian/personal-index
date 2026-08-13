# TICKET-11-4: Extract helpers from `url_classifier.URLClassifier.classify` (59L → ~20L)

## File
`personal_index/url_classifier.py`, lines 103–161

## Evidence

The `classify` method contains six near-identical pattern-matching blocks, each following the same structure:
