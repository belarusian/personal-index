# TICKET-495: normalize_batch docstring is generic — pin exact contract

- File: personal_index/content_transform/normalizer.py
- Function: ContentNormalizer.normalize_batch (lines ~56-67)
- Symptom: Docstring says only "Normalize multiple content items." with generic
  Args/Returns. The code has a distinct contract worth pinning:
  (1) returns a NEW list (list comprehension) — input list never mutated, result
      is not the input object;
  (2) each item normalized via self.normalize(item), order preserved, each output
      item is a new dict (not the input item object);
  (3) empty input list -> empty list (no error).
- Evidence (verified live):
  - result is not items: True
  - input unchanged: True
  - each out is not inp: True
  - empty -> [] (list)
- Minimal additive fix: reword the docstring to state the three behaviors; append
  TestNormalizeBatchPinning to tests/test_content_transform.py (mirror
  TestTransformBatchPinning).
- Issue: #844
