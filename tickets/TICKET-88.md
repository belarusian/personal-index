# TICKET-88: Type error — `ContentTagger.TagResult` is a variable alias, not valid as a type

## Title
`ContentTagger.TagResult` is a class-level variable assignment, not a proper nested class — mypy rejects it as a type

## Evidence
File: `personal_index/content_tagger/tagger.py`
Line 34: `TagResult = TagResult  # Expose as nested class for API convenience`

This creates a class attribute that shadows the module-level `TagResult` dataclass. mypy flags:
- Line 40: `Variable "personal_index.content_tagger.tagger.ContentTagger.TagResult" is not valid as a type  [valid-type]`
- Line 53: `Variable "personal_index.content_tagger.tagger.ContentTagger.TagResult" is not valid as a type  [valid-type]`

The return type annotations on `tag()` (line 40) and `batch_tag()` (line 53) use `TagResult` which mypy resolves to the class attribute rather than the module-level dataclass.

## Impact
Type checkers cannot validate the return types of `tag()` and `batch_tag()` methods. IDE autocomplete may also be confused.

## Suggestion
Either:
1. Remove the alias and use `personal_index.content_tagger.tagger.TagResult` in return annotations
2. Or properly define `TagResult` as a nested class inside `ContentTagger`
3. Or use `TYPE_CHECKING` guard to make the alias available only for type checkers
