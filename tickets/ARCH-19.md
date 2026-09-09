Status: IMPLEMENTED PR #1127@b4de26c (cycle 202: content_tagger substring docstring + dead weight removal + pinning tests)
Kind: ARCH
Author: architect (cycle 181)
Issue: #1054

# ARCH-19: content_tagger — substring keyword matching + dead `weight` field

## Component
`personal_index/content_tagger/` (home: `docs/content-tagger.md`).
Two related contract holes in the topic-detection engine.

## Symptom

1. **Substring (non-word-boundary) keyword matching.** `TopicDetector.detect`
   counts keyword occurrences with `re.findall(re.escape(kw_lower), text_lower)`,
   which matches keywords as **substrings**, not whole words. Short keywords
   therefore match inside longer words: `"ai"` matches inside "said"/"maintain",
   `"sql"` inside "nosql", `"index"` inside "indexes", `"model"` inside
   "modeling", `"training"` inside "retraining". The `detect` docstring says
   "keyword occurrences" without stating the substring semantics, so a reader
   who expects word-boundary matching is surprised by false-positive topic
   matches.

2. **Dead `weight` field.** `_TopicDefinition.weight` is stored (default
   `1.0`) and `TopicDetector.add_topic(..., weight=...)` accepts it, but
   `detect`'s confidence formula (`0.5 + match_count * 0.1`) never reads
   `weight`. The parameter is silently ignored, so a caller who passes a
   weight to bias a topic gets no effect.

## Public contract (the fix)

### Hole 1 — state the matching semantics (docstring, no behavior change)
`TopicDetector.detect`'s docstring MUST state the exact matching rule:
keywords are matched **case-insensitively as substrings** (via
`re.findall(re.escape(keyword.lower()), text.lower())`), NOT as whole words.
State that a keyword may match inside a longer word (e.g. `"ai"` inside
"said"), so the substring semantics are part of the contract, not an
implementation detail.

### Hole 2 — remove the dead `weight` parameter (behavior-neutral)
Either (a) drop `weight` from `_TopicDefinition` and from
`TopicDetector.add_topic`'s signature, or (b) keep it and state in the
docstring that it is currently unused. Option (a) is preferred: a parameter
that does nothing is a contract lie. If (a) is chosen, `add_topic`'s
signature becomes `add_topic(self, name: str, keywords: list[str])`.

## Acceptance criteria
1. `docs/content-tagger.md` states the substring-matching semantics in the
   `detect` contract (already written in cycle 181; keep it in sync with the
   code change).
2. `TopicDetector.detect`'s docstring states the substring (non-word-boundary)
   matching rule (implementer work).
3. The dead `weight` field/parameter is removed (option a) OR explicitly
   documented as unused (option b) (implementer work).
4. Pinning tests below pass.

## Scope split (architect vs implementer)
- **Architect (this ticket, docs/ + ticket only):** `docs/content-tagger.md`
  spec page (written in cycle 181) + this ticket. No code/docstring/test
  changes in this pass.
- **Implementer (later, code):** (a) reword `detect`'s docstring to state the
  substring semantics, (b) remove or document the dead `weight`, (c) add the
  pinning tests below.

## Pinning tests to add
1. **Substring match (hole 1):** assert `TopicDetector().detect("said")`
   emits an `ai` tag (keyword `"ai"` matches inside "said"), pinning the
   substring semantics against the returned object.
2. **Guard path (hole 1):** assert `TopicDetector().detect("")` and
   `detect("   ")` both return `[]` (falsy / whitespace-only guard).
3. **Dead weight (hole 2):** if option (a) is chosen, assert
   `inspect.signature(TopicDetector.add_topic).parameters` has no `weight`
   key; if option (b), assert the docstring contains an "unused" note.
