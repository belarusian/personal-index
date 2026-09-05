# TICKET-398

- Status: OPEN
- Issue: #634
- Module: personal_index/content_summarizer.py
- Function: _score_sentence (line 94)
- Class: (b) doc-drift — generic single-line docstring

## Symptom
Docstring `"""Score a sentence based on word frequencies."""` is a generic
placeholder that does not enumerate the actual behavior. It hides that the
returned value is the MEAN per-token frequency (sum of word_freq.get(w,0) over
tokens divided by the token count), not the raw sum, and that an empty
tokenization returns 0.0.

## Evidence
personal_index/content_summarizer.py:95
    """Score a sentence based on word frequencies."""
Body (lines 96-101):
    words = _tokenize(sentence)
    if not words:
        return 0.0
    score = sum(word_freq.get(w, 0) for w in words)
    return score / len(words)

## Minimal additive fix
Reword the docstring to state the exact behavior: tokenizes the sentence,
returns 0.0 when no tokens, else returns the mean per-token frequency
(sum of word_freq.get(w,0) over tokens / token count). Add ONE pinning test
asserting the corrected mean-vs-sum claim against the returned float.

## Line-shift guard
tests/test_content_summarizer.py references _score_sentence only by direct
call (lines 83,87,91); the only getsource is summarize_page (line 196), which
resolves by function object. Adding docstring lines is safe.
