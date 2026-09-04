# TICKET-339: content_summarizer.summarize_page docstring over-promises "keyword boost" for the title

Status: RESOLVED
Module: personal_index/content_summarizer.py
Class: (b) docstring over-promises behavior the code does not do

## Symptom
`summarize_page` docstring reads:
    """Summarize a page using title and content.

    The title is used as a keyword boost for sentence scoring.
    ...
    """
The body (content_summarizer.py:177-179) does NOT apply any title-specific
keyword boost. It simply prepends the title to the content and summarizes the
combined text:
    combined = f"{title}. {content}"
    return summarize(combined, max_sentences=max_sentences)
The title's words enter the word-frequency map at normal weight (via
`_word_frequency(combined)` inside `summarize`); there is no multiplier,
re-weighting, or special handling keyed on the title. The title merely becomes
the first sentence of the combined text, which receives the standard
positional `i == 0` boost in `_score_and_select` (applied to the first
sentence of ANY text, not a title-specific keyword boost). The docstring
therefore over-promises a "keyword boost" mechanism the code does not perform;
the code only "prepends the title to the content before summarizing".

## Evidence
personal_index/content_summarizer.py:155  ("""Summarize a page using title and content.")
personal_index/content_summarizer.py:157  (The title is used as a keyword boost for sentence scoring.)
personal_index/content_summarizer.py:177  (# Combine title with content for scoring)
personal_index/content_summarizer.py:178  (combined = f"{title}. {content}")
personal_index/content_summarizer.py:179  (return summarize(combined, max_sentences=max_sentences))
No title-keyed weighting exists anywhere in the module (grep "title" shows only
the param, docstring, empty-content branch, and the prepend at line 178).

## Minimal additive fix
Reword the `summarize_page` docstring to what the code actually does:
    """Summarize a page using title and content.

    The title is prepended to the content before summarizing.
    ...
    """
Do NOT change the returned summary (behavior change, out of scope).

## Regression test
Assert via inspect.getsource that the summarize_page docstring no longer claims
"keyword boost", and that summarize_page still prepends the title to the
content (behavior unchanged: a title word that is frequent in the content
still influences the summary, and the title becomes the first sentence).

Issue: #516
