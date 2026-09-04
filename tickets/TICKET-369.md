# TICKET-369 — get_keywords leaks heading-level markers (h1/h2/h3) into the keyword set

- Status: OPEN
- Class: (a) behavioral
- Module: personal_index/content.py
- Issue: #576

## Symptom
ExtractedContent.get_keywords() extracts words from headings via
re.findall(r'[a-z0-9]+', heading.lower()). Headings are stored by
_extract_headings as f"h{level}: {text}" (e.g. "h1: Python Tutorial"), so the
level marker h1/h2/h3 is captured by the regex and returned as a "keyword".
The docstring promises keywords from the heading words, not the structural
level prefix.

## Evidence
Reproduced against current main (e509712):
  c = ExtractedContent(url='http://x', meta_keywords=['python'],
                       headings=['h1: Python Tutorial', 'h2: Advanced Guide'])
  sorted(c.get_keywords())
  -> ['advanced', 'guide', 'h1', 'h2', 'python', 'tutorial']
  'h1' in c.get_keywords() -> True

## Minimal additive fix
In get_keywords, strip the hN: level prefix before extracting words, so only
the heading text contributes keywords. Keep the rest of the method unchanged.

## Test
Add a test asserting that a heading's level marker (h1) is NOT in the keyword
set while the heading's real words ARE. Fails pre-fix, passes post-fix.
