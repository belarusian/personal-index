# TICKET-508: Suggestion.to_dict placeholder docstring under-describes behavior

Status: RESOLVED

## File
`personal_index/search_suggestions.py` — `Suggestion.to_dict` (line ~23)

## Symptom
The docstring is the placeholder `"""To_dict."""`, which omits the actual contract:
the method returns a NEW `dict` with exactly the keys `text`, `score`, `source`,
`category`; `score` is rounded to 4 decimal places (via `round(self.score, 4)`);
`text`, `source`, and `category` are copied by reference; the suggestion object is
NOT mutated.

## Evidence
Live read of `personal_index/search_suggestions.py` lines 23-31:
    def to_dict(self) -> dict[str, Any]:
        """To_dict."""
        return {
            "text": self.text,
            "score": round(self.score, 4),
            "source": self.source,
            "category": self.category,
        }
`round(self.score, 4)` confirms score is rounded to 4 decimals. The other three
fields are returned by reference. No mutation of `self` occurs.

## Minimal additive fix
Reword ONLY `to_dict`'s docstring to state the exact contract above (including the
score rounding). Do not touch any other function in search_suggestions.py. Append
pinning tests to `tests/test_search_suggestions.py`: pin return type `dict`, exact
key set, and score rounding to 4 decimals.

## Issue
Issue: #873
