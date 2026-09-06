# TICKET-490: ContentMatcher.relevance_score returns 0.0 for REGEX-mode interests that match content (class-(a) behavioral)

- File: personal_index/filter/matcher.py
- Method: ContentMatcher.relevance_score (and its consumers InterestFilter.matches / should_index / filter_content)
- Symptom (class-(a) behavioral): `relevance_score` counts LITERAL substring
  occurrences of each keyword via `text_lower.count(kw.lower())`. For
  `MatchMode.REGEX` the "keywords" are regex patterns, so the pattern string
  (e.g. `py\w+`) never appears literally in the text and the score is always
  0.0. `matches_content` correctly returns True for a REGEX match, but
  `InterestFilter.matches` only keeps an interest when `score > best_score`
  (0.0 > 0.0 is False), so a REGEX-mode interest that matches content is
  silently dropped -> `matches` returns None and `should_index` returns False,
  contradicting `matches_content`. ANY/ALL modes are unaffected (literal
  substring count is the intended semantics there).
- Evidence:
  - personal_index/filter/matcher.py:55-68 (relevance_score: `total += text_lower.count(kw.lower())` for every keyword regardless of match_mode)
  - personal_index/filter/matcher.py:84-92 (matches: `if score > best_score` gate drops a 0.0 REGEX match)
  - Repro: Interest(keywords=[r"py\w+"], match_mode=REGEX) -> matches_content("python is great") is True, relevance_score(...) is 0.0, InterestFilter([i]).matches("python is great") is None.
- Minimal additive fix: in `relevance_score`, when `match_mode == MatchMode.REGEX`,
  count matches with `len(re.findall(kw, text, re.IGNORECASE))` (guarding
  `re.error`) instead of the literal substring count; keep the existing literal
  count for ANY/ALL. This makes a REGEX content match produce a positive score
  so `InterestFilter.matches`/`should_index` keep it, consistent with
  `matches_content`.
