"""Content filtering package."""
from personal_index.filter.matcher import ContentMatcher, InterestFilter
from personal_index.filter.engine import ContentFilter, FilterResult

__all__ = [
    "ContentFilter",
    "FilterResult",
    "ContentMatcher",
    "InterestFilter",
]
