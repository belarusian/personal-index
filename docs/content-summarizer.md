# Content Summarizer (spec)

`personal_index.content_summarizer` — extractive summarization of text using
sentence scoring based on keyword frequency. No external dependencies; pure
`re` + `dataclasses`.

## Public API

### `SummaryResult` (dataclass)
The return object of every public function. Fields, in order:
- `original_text: str` — the text that was summarized (for `summarize_page`
  with non-empty content this is the combined `"<title>. <content>"` string,
  not the raw title or content).
- `summary: str` — the space-joined selected sentences.
- `sentences: list[str]` — the selected sentence strings (in original order).
- `ratio: float` — `word_count_summary / max(word_count_original, 1)`.
- `word_count_original: int` — `len(_tokenize(original_text))`.
- `word_count_summary: int` — `len(_tokenize(summary))`.
- `__str__` returns `self.summary`.

### `summarize(text: str, max_sentences: int = 3, min_length: int = 50) -> SummaryResult`
Behavior, in order:
1. **Guard path:** if `text` is falsy or `len(text) < min_length` (default 50),
   return `_no_op_result(text)` — a `SummaryResult` whose `summary` equals
   `text`, `ratio` is `1.0`, `sentences` is `[text]` (or `[]` when `text` is
   empty), and both word counts are `len(_tokenize(text))`. No splitting or
   scoring occurs.
2. **Short-text path:** split `text` via `_split_sentences`; if the sentence
   count is `<= max_sentences`, return `_build_summary_result(text, sentences)`
   keeping ALL sentences (no scoring, no selection).
3. **Scoring path:** otherwise compute `_word_frequency(text)` and select the
   top `max_sentences` via `_score_and_select` (the first sentence is boosted
   x2.5 and the last x1.1 before ranking), then return
   `_build_summary_result(text, selected)`.

### `summarize_page(title: str, content: str, max_sentences: int = 3) -> SummaryResult`
- **Guard path:** if `content` is falsy, return a `SummaryResult` with
  `original_text=title`, `summary=""`, `sentences=[]`, `ratio=0.0`,
  `word_count_original=len(_tokenize(title))`, `word_count_summary=0`.
- Otherwise build `combined = f"{title}. {content}"` and return
  `summarize(combined, max_sentences=max_sentences)`. Note the title is
  prepended with a `". "` separator; the returned `original_text` is the
  combined string, not `title`.
- **Reachability:** `summarize_page` is a standalone public utility — it is
  NOT reachable from the CLI or the pipeline; page summaries are only
  available via direct API use (import and call `summarize_page`).

## Private helpers (the code is the truth)
- `_split_sentences(text) -> list[str]` — normalizes all whitespace runs to a
  single space and strips; returns `[]` when the normalized text is empty.
  Otherwise splits on `(?<=[.!?])\s+(?=[A-Z])` (sentence-ending punctuation
  followed by whitespace and an uppercase letter), strips each fragment, and
  drops empties. No abbreviation table or lookahead.
- `_tokenize(text) -> list[str]` — `re.findall(r'[a-z0-9]+', text.lower())`;
  splits on any non-alphanumeric (punctuation, spaces, apostrophes all act as
  separators) and keeps digit runs as their own tokens. Empty / all-punctuation
  input yields `[]`.
- `STOPWORDS: frozenset[str]` — module-level stopword set (articles,
  prepositions, pronouns, auxiliaries, common adverbs, and contraction
  fragments such as `"s"`, `"t"`, `"don"`, `"ll"`, `"m"`, `"ve"`, `"ain"`,
  `"wouldn"`).
- `_word_frequency(text) -> dict[str, int]` — tokenizes, skips tokens in
  `STOPWORDS`, skips tokens with `len(word) <= 2`, accumulates counts in a
  plain dict.
- `_score_sentence(sentence, word_freq) -> float` — tokenizes; returns `0.0`
  when no tokens; otherwise the **mean** per-token frequency
  (`sum(word_freq.get(w, 0) for w in words) / len(words)`), not the raw sum,
  so a short sentence of frequent words can outscore a long one.
- `_score_and_select(sentences, word_freq, max_sentences) -> list[str]` —
  scores each sentence, multiplies index 0 by 2.5 and the last index by 1.1,
  sorts by score descending, takes the top `max_sentences`, then re-sorts the
  selected by original index (so the summary preserves document order).
- `_build_summary_result(text, summary_sentences) -> SummaryResult` — joins the
  sentences with a single space and computes the counts/ratio as above.
- `_no_op_result(text) -> SummaryResult` — the guard-path builder described in
  `summarize`.

## Contract holes
- **`summarize_page` is a standalone public utility (no pipeline or CLI
  caller).** `summarize_page` is exported and tested, but no code in
  `personal_index/` (pipeline, CLI, orchestrator) calls it. It is a standalone
  public utility: page summaries are NOT produced by the product's pipeline or
  CLI; callers import `summarize_page` directly and use it via the public API.
  Resolved by documentation (ARCH-14).
- **`summarize_page` guard path returns `ratio=0.0` while `summarize`'s guard
  path returns `ratio=1.0`.** For empty content the page summary is empty
  (`ratio=0.0`), but for short/empty text `summarize` returns the text as-is
  (`ratio=1.0`). The two guard paths encode different "no-op" semantics for the
  same conceptual case (nothing to summarize), which is easy to misread as a
  bug. Documented here as the current behavior; no ticket (intentional, but
  worth a reader note).
