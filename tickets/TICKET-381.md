# TICKET-381

- file: personal_index/content_extractor.py
- symptom: ContentExtractor.extract() leaks the page <title> text into
  content.text (and therefore into word_count and the readability score),
  duplicating the title into the body content.
- evidence: _extract_text() calls soup.get_text(separator=" ", strip=True)
  over the WHOLE soup (lines 139-145). The <title> tag lives in <head> and is
  never decomposed (only script/style/noscript are, line 53), so its text is
  included. Probe: extract('<html><head><title>My Page Title</title></head>
  <body><p>Body content here</p></body></html>').text ==
  'My Page Title Body content here' (title leaked). word_count is inflated by
  the title words and extract_readability_score() scores the title words.
  Downstream (pipeline.py:484-487) consumes title and text separately, so the
  title is double-counted.
- minimal additive fix: in _extract_text(), decompose the <title> tag (if
  present) before calling get_text(), so visible body text excludes the page
  title. Additive: body text, headings, links, images, meta, canonical,
  language are all unchanged; only the title text is removed from text.
- class: (a) behavioral
- Issue: #600
