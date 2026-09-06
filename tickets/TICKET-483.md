# TICKET-483: ContentNormalizer._normalize_tag docstring is generic (class-(b) doc-drift)

Status: OPEN
File: personal_index/content_transform/normalizer.py
Method: ContentNormalizer._normalize_tag

## Symptom
The docstring is the generic "Normalize tag format." but the code performs four
specific, contract-bearing transformations.

## Evidence (lines 92-99)
```python
def _normalize_tag(self, tag: str) -> str:
    """Normalize tag format."""
    tag = tag.strip().lower()
    tag = re.sub(r"[^a-z0-9-]", "-", tag)
    tag = re.sub(r"-+", "-", tag)
    return tag.strip("-")
```

## Actual behavior (verified)
1. strips surrounding whitespace and lowercases the value;
2. replaces every character not in [a-z0-9-] with a single "-";
3. collapses runs of consecutive "-" into one "-";
4. strips leading and trailing "-".

Verified examples:
- "  My Tag  " -> "my-tag"
- "Hello_World" -> "hello-world"
- "a--b" -> "a-b"
- "-lead" -> "lead"
- "trail-" -> "trail"
- "a.b.c" -> "a-b-c"
- "123" -> "123"
- "" -> ""

## Minimal additive fix
- Reword the _normalize_tag docstring to state exactly those four behaviors.
- Append a TestNormalizeTagPinning class to tests/test_content_transform.py
  covering the 8 examples above.

Issue: #816
