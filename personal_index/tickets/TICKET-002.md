# TICKET-002: mypy error — `in` operator on `set[str] | None` in tokenizer

**File:** `personal_index/content_search/tokenizer.py:50,71`

**What's wrong:**
`self.stopwords` is typed as `set[str] | None`, but `__post_init__` initializes it to a default set if None. However, mypy doesn't track that mutation, so at lines 50 and 71 the `in` operator is used on a value that could still be `None`.

**Evidence:**
