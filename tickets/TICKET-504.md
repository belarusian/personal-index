# TICKET-504: EncodingDetector.detect docstring omits detection priority and confidence contract

## Symptom
The `EncodingDetector.detect` docstring reads `"""Detect the encoding of byte data."""` which is generic and omits the actual detection priority cascade and confidence values that the implementation delivers.

## Evidence
personal_index/encoding.py:25-34
```python
def detect(self, data: bytes) -> EncodingResult:
    """Detect the encoding of byte data."""
```

Live behavior verified:
- UTF-8 BOM → encoding=utf-8, confidence=1.0
- UTF-16 BOM (LE/BE) → encoding=utf-16, confidence=1.0
- ASCII → encoding=ascii, confidence=0.9 (takes priority over valid UTF-8)
- Valid UTF-8 non-ASCII → encoding=utf-8, confidence=0.8
- Fallback → encoding=iso-8859-1, confidence=0.5
- Empty bytes → encoding=ascii, confidence=0.9

## Minimal Additive Fix
Reword the docstring to state the exact detection priority order and confidence values, and append pinning tests to tests/test_encoding.py.

Issue: #862

## Status
OPEN

## Resolution
RESOLVED via PR #863 (merged 2026-09-06)
