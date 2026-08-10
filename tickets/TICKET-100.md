# TICKET-100: F401 — Self-import of `TagResult` as `_TagResult` in `content_tagger/tagger.py` is unused

## Title
`personal_index/content_tagger/tagger.py` imports itself inside a `TYPE_CHECKING` block but never uses the alias

## Evidence
File: `personal_index/content_tagger/tagger.py`

Line 12: `from personal_index.content_tagger.tagger import TagResult as _TagResult`

This is a self-import — the module imports its own `TagResult` class (defined at line 16) under the alias `_TagResult`, inside a `TYPE_CHECKING` block:
