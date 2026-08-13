# TICKET-11-1: Extract helpers from `cli_verify._check_full_pipeline` (73L → ~30L)

## File
`personal_index/cli_verify.py`, lines 138–210

## Evidence

The function `_check_full_pipeline` performs three distinct logical phases:

1. **Test content creation** (lines 151–157): Creates a temp directory and writes a test `.txt` file.
2. **Pipeline component setup** (lines 160–169): Instantiates `InterestStore`, `TagStore`, `SearchIndex`, `ContentFilter`, `ContentScorer` with temp paths.
3. **Pipeline execution** (lines 172–205): Reads file → builds `CrawledPage` → filter → score → tag → index → search → validate.

All three phases are sequential and self-contained. The function body is 73 lines with no sub-extraction.

## Impact

- Hard to unit-test individual phases (e.g., testing just the pipeline execution without file I/O).
- Violates single-responsibility: file creation, component wiring, and pipeline logic are mixed.
- The `import shutil` at line 144 is inside the function body — should be at module level.

## Suggestion

Extract two private helpers:

### Helper 1: `_create_test_content`
