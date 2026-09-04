# TICKET-338: results.ResultsFormatter.create_snippet docstring over-promises "highlighting the query"

Status: RESOLVED
Module: personal_index/results.py
Class: (b) docstring over-promises behavior the code does not do

## Symptom
`ResultsFormatter.create_snippet` docstring reads:
    """Create a snippet highlighting the query."""
The body (results.py:63-78) only locates the query's index in the text and
returns a window around it (`text[start:end]`), prefixing/suffixing `...`
ellipses when the window is clipped. It never adds any emphasis, markup, or
case change to the query itself — the query appears in the snippet exactly as
it appears in the source text. Verified: for text
"The quick brown fox jumps over the lazy dog near the river bank today" and
query "fox", the returned snippet contains "fox" with no `**`, `<b>`, `<mark>`,
`__`, or `//` markup. The docstring therefore over-promises "highlighting"
when the code only "centers a window around the query".

## Evidence
personal_index/results.py:59  (def create_snippet(self, text, query, max_length=200) -> str:)
personal_index/results.py:62  ("""Create a snippet highlighting the query.""")
personal_index/results.py:65-78 (idx = text.lower().find(query_lower); start/end window; snippet = text[start:end]; "..." ellipses only)

## Minimal additive fix
Reword the `create_snippet` docstring to what the code actually does:
    """Create a snippet centered on the query."""
Do NOT change the returned snippet (behavior change, out of scope).

## Regression test
Assert via inspect.getsource that the create_snippet docstring no longer claims
"highlighting", and that create_snippet returns a plain (un-highlighted) window
around the query (behavior unchanged).

Issue: #514
