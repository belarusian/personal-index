"""Content filtering package."""
from personal_index.filter.engine import ContentFilter, FilterResult
from personal_index.filter.matcher import ContentMatcher, InterestFilter

__all__ = [
    "ContentFilter",
    "ContentMatcher",
    "FilterResult",
    "InterestFilter",
]
