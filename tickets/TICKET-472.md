# TICKET-472: content_type.py detect_from_bytes docstring under-promise

## File
personal_index/content_type.py

## Symptom
The `detect_from_bytes` method's docstring says "Detect content type from raw bytes (magic number detection)." but the method does more than magic number detection: it also falls back to text detection (UTF-8 decode with null-byte check) when no magic number matches, and returns unknown for empty input. The docstring under-promises by omitting the text detection fallback and the empty-input guard.

## Evidence
Line ~237: "Detect content type from raw bytes (magic number detection)."
Lines ~243-253: The method body:
1. `if not data: return self._unknown_type()` (empty guard)
2. `result = self._check_magic_numbers(data)` (magic number detection)
3. `text_result = self._try_detect_text(data)` (text detection fallback)
4. `return self._unknown_type()` (final fallback)

The docstring only mentions "magic number detection" but the method also does text detection as a fallback.

## Minimal Additive Fix
Reword the docstring to state the exact sequence: "Detect content type from raw bytes. Tries magic number detection first, then falls back to text detection (UTF-8 decode with null-byte check), returning unknown if neither matches. Empty input returns unknown."

Add ONE behavior test that pins the corrected claim:
- Normal path: PDF bytes → returns application/pdf (magic number path).
- Guard path: non-magic-number text bytes (UTF-8, no null bytes) → returns text/plain (text fallback path).
- Guard path: empty bytes → returns unknown (empty input guard).

## Guard-Path Pin
The test includes the text fallback input (non-magic-number text bytes) alongside the magic number input (PDF bytes) and the empty input, so one test pins all three paths: magic number detection, text detection fallback, and empty input guard.
Issue: #790
