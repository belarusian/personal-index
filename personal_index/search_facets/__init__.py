"""Search facets module - filterable search dimensions."""

from personal_index.search_facets.facet import Facet, FacetType, FacetValue
from personal_index.search_facets.facet_builder import FacetBuilder
from personal_index.search_facets.faceted_search import FacetedSearch, SearchResults

__all__ = [
    "Facet",
    "FacetBuilder",
    "FacetType",
    "FacetValue",
    "FacetedSearch",
    "SearchResults",
]
