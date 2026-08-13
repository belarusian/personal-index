"""Tests for search_facets module - filterable search dimensions."""


from personal_index.search_facets.facet import Facet, FacetType, FacetValue
from personal_index.search_facets.facet_builder import FacetBuilder
from personal_index.search_facets.faceted_search import FacetedSearch, SearchResults

# ── Facet model tests ──────────────────────────────────────

class TestFacet:
    def test_create_facet(self):
        facet = Facet(name="category", facet_type=FacetType.CATEGORY)
        assert facet.name == "category"
        assert facet.facet_type == FacetType.CATEGORY

    def test_facet_add_value(self):
        facet = Facet(name="tag", facet_type=FacetType.TAG)
        facet.add_value("python", count=5)
        assert len(facet.values) == 1
        assert facet.values[0].name == "python"
        assert facet.values[0].count == 5

    def test_facet_multiple_values(self):
        facet = Facet(name="tag", facet_type=FacetType.TAG)
        facet.add_value("python", count=5)
        facet.add_value("javascript", count=3)
        assert len(facet.values) == 2

    def test_facet_to_dict(self):
        facet = Facet(name="domain", facet_type=FacetType.STRING)
        facet.add_value("example.com", count=10)
        d = facet.to_dict()
        assert d["name"] == "domain"
        assert len(d["values"]) == 1

    def test_facet_from_dict(self):
        d = {
            "name": "date",
            "facet_type": "date",
            "values": [{"name": "2024-01", "count": 5}],
        }
        facet = Facet.from_dict(d)
        assert facet.name == "date"
        assert facet.facet_type == FacetType.DATE

    def test_facet_equality(self):
        f1 = Facet(name="tag", facet_type=FacetType.TAG)
        f2 = Facet(name="tag", facet_type=FacetType.TAG)
        assert f1 == f2

    def test_facet_sort_values(self):
        facet = Facet(name="tag", facet_type=FacetType.TAG)
        facet.add_value("b", count=1)
        facet.add_value("a", count=10)
        facet.add_value("c", count=5)
        facet.sort_values()
        assert facet.values[0].name == "a"


class TestFacetValue:
    def test_create_value(self):
        fv = FacetValue(name="python", count=5)
        assert fv.name == "python"
        assert fv.count == 5

    def test_value_to_dict(self):
        fv = FacetValue(name="test", count=3)
        d = fv.to_dict()
        assert d == {"name": "test", "count": 3}

    def test_value_from_dict(self):
        fv = FacetValue.from_dict({"name": "x", "count": 7})
        assert fv.name == "x"
        assert fv.count == 7


class TestFacetType:
    def test_facet_type_values(self):
        assert FacetType.CATEGORY.value == "category"
        assert FacetType.TAG.value == "tag"
        assert FacetType.DATE.value == "date"
        assert FacetType.STRING.value == "string"
        assert FacetType.NUMBER.value == "number"
        assert FacetType.BOOLEAN.value == "boolean"

    def test_facet_type_count(self):
        assert len(FacetType) == 6


# ── FacetBuilder tests ─────────────────────────────────────

class TestFacetBuilder:
    def test_build_from_items(self):
        builder = FacetBuilder()
        items = [
            {"tags": ["python", "web"], "domain": "example.com", "date": "2024-01-01"},
            {"tags": ["python", "api"], "domain": "test.com", "date": "2024-01-15"},
            {"tags": ["javascript", "web"], "domain": "example.com", "date": "2024-02-01"},
        ]
        facets = builder.build(items, facet_fields=["tags", "domain"])
        assert len(facets) == 2

    def test_build_empty(self):
        builder = FacetBuilder()
        facets = builder.build([], facet_fields=["tags"])
        assert len(facets) == 0

    def test_build_tag_facet(self):
        builder = FacetBuilder()
        items = [
            {"tags": ["python"]},
            {"tags": ["python", "web"]},
            {"tags": ["web"]},
        ]
        facets = builder.build(items, facet_fields=["tags"])
        tag_facet = facets.get("tags")
        assert tag_facet is not None
        python_val = next((v for v in tag_facet.values if v.name == "python"), None)
        assert python_val is not None
        assert python_val.count == 2

    def test_build_date_facet(self):
        builder = FacetBuilder()
        items = [
            {"date": "2024-01-01"},
            {"date": "2024-01-15"},
            {"date": "2024-02-01"},
        ]
        facets = builder.build(items, facet_fields=["date"])
        date_facet = facets.get("date")
        assert date_facet is not None

    def test_build_with_limit(self):
        builder = FacetBuilder()
        items = [{"tags": [f"tag{i}"]} for i in range(20)]
        facets = builder.build(items, facet_fields=["tags"], max_values=5)
        tag_facet = facets.get("tags")
        assert tag_facet is not None
        assert len(tag_facet.values) <= 5

    def test_build_nested_fields(self):
        builder = FacetBuilder()
        items = [
            {"metadata": {"author": "alice"}},
            {"metadata": {"author": "bob"}},
        ]
        facets = builder.build(items, facet_fields=["metadata.author"])
        assert "metadata.author" in facets

    def test_custom_facet_type(self):
        builder = FacetBuilder()
        items = [{"score": 5}, {"score": 10}]
        facets = builder.build(items, facet_fields=["score"], facet_types={"score": "number"})
        score_facet = facets.get("score")
        assert score_facet is not None
        assert score_facet.facet_type == FacetType.NUMBER

    def test_aggregate_facets(self):
        builder = FacetBuilder()
        f1 = builder.build([{"tags": ["a", "b"]}], facet_fields=["tags"])
        f2 = builder.build([{"tags": ["b", "c"]}], facet_fields=["tags"])
        merged = builder.aggregate(f1, f2)
        assert "tags" in merged


# ── FacetedSearch tests ────────────────────────────────────

class TestFacetedSearch:
    def test_add_document(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Python tutorial", "tags": ["python", "tutorial"]})
        assert len(search.get_documents()) == 1

    def test_search_with_facets(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Python tutorial", "tags": ["python"]})
        search.add_document("id2", {"title": "JS guide", "tags": ["javascript"]})
        results = search.search("python", facet_fields=["tags"])
        assert len(results["results"]) >= 1
        assert "facets" in results

    def test_search_no_results(self):
        search = FacetedSearch()
        results = search.search("nonexistent")
        assert len(results["results"]) == 0

    def test_filter_by_facet(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Python", "category": "programming"})
        search.add_document("id2", {"title": "Recipe", "category": "cooking"})
        results = search.search("", filters={"category": "programming"})
        assert len(results["results"]) == 1
        assert results["results"][0]["id"] == "id1"

    def test_filter_multiple_facets(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "A", "category": "tech", "level": "beginner"})
        search.add_document("id2", {"title": "B", "category": "tech", "level": "advanced"})
        search.add_document("id3", {"title": "C", "category": "cooking", "level": "beginner"})
        results = search.search("", filters={"category": "tech", "level": "beginner"})
        assert len(results["results"]) == 1

    def test_get_available_facets(self):
        search = FacetedSearch()
        search.add_document("id1", {"tags": ["python"], "category": "tech"})
        facets = search.get_available_facets()
        assert "tags" in facets
        assert "category" in facets

    def test_search_with_pagination(self):
        search = FacetedSearch()
        for i in range(10):
            search.add_document(f"id{i}", {"title": f"Doc {i}", "tags": ["test"]})
        results = search.search("", page=1, page_size=3)
        assert len(results["results"]) <= 3
        assert results["page"] == 1
        assert results["page_size"] == 3

    def test_remove_document(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Test"})
        search.remove_document("id1")
        assert len(search.get_documents()) == 0

    def test_search_result_to_dict(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Test", "tags": ["a"]})
        results = search.search("test")
        d = results.to_dict()
        assert "results" in d
        assert "facets" in d

    def test_clear_all(self):
        search = FacetedSearch()
        search.add_document("id1", {"title": "Test"})
        search.clear()
        assert len(search.get_documents()) == 0


# ── FacetedSearchFilters tests (ISSUE #287) ────────────────

class TestFacetedSearchFilters:
    """Tests for filter operators: $gte, $lte, $gt, $lt, $between, $in, $not."""

    def _setup_search_with_scores(self) -> FacetedSearch:
        search = FacetedSearch()
        search.add_document("d1", {"title": "Low", "score": 10, "category": "a"})
        search.add_document("d2", {"title": "Mid", "score": 50, "category": "b"})
        search.add_document("d3", {"title": "High", "score": 90, "category": "a"})
        search.add_document("d4", {"title": "Max", "score": 100, "category": "c"})
        return search

    # -- $gte --
    def test_filter_gte(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$gte": 50}})
        ids = [r["id"] for r in results["results"]]
        assert "d2" in ids
        assert "d3" in ids
        assert "d4" in ids
        assert "d1" not in ids

    # -- $lte --
    def test_filter_lte(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$lte": 50}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" in ids
        assert "d3" not in ids
        assert "d4" not in ids

    # -- $gt --
    def test_filter_gt(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$gt": 50}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" not in ids
        assert "d2" not in ids
        assert "d3" in ids
        assert "d4" in ids

    # -- $lt --
    def test_filter_lt(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$lt": 50}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids
        assert "d3" not in ids
        assert "d4" not in ids

    # -- $between --
    def test_filter_between(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$between": [10, 50]}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" in ids
        assert "d3" not in ids
        assert "d4" not in ids

    # -- $in --
    def test_filter_in(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$in": [10, 90]}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d3" in ids
        assert "d2" not in ids
        assert "d4" not in ids

    # -- $not --
    def test_filter_not(self):
        search = self._setup_search_with_scores()
        results = search.search("", filters={"score": {"$not": 50}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids
        assert "d3" in ids
        assert "d4" in ids

    # -- Date range filters with ISO strings --
    def test_filter_date_gte_iso(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "Jan", "date": "2024-01-15"})
        search.add_document("d2", {"title": "Mar", "date": "2024-03-01"})
        search.add_document("d3", {"title": "Jun", "date": "2024-06-10"})
        results = search.search("", filters={"date": {"$gte": "2024-03-01"}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" not in ids
        assert "d2" in ids
        assert "d3" in ids

    def test_filter_date_lte_iso(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "Jan", "date": "2024-01-15"})
        search.add_document("d2", {"title": "Mar", "date": "2024-03-01"})
        search.add_document("d3", {"title": "Jun", "date": "2024-06-10"})
        results = search.search("", filters={"date": {"$lte": "2024-03-01"}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" in ids
        assert "d3" not in ids

    def test_filter_date_between_iso(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "Jan", "date": "2024-01-15"})
        search.add_document("d2", {"title": "Mar", "date": "2024-03-01"})
        search.add_document("d3", {"title": "Jun", "date": "2024-06-10"})
        results = search.search("", filters={"date": {"$between": ["2024-01-01", "2024-03-31"]}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" in ids
        assert "d3" not in ids

    # -- Nested dot-notation field access --
    def test_filter_nested_dot_notation(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "metadata": {"author": "alice", "score": 80}})
        search.add_document("d2", {"title": "B", "metadata": {"author": "bob", "score": 60}})
        results = search.search("", filters={"metadata.author": "alice"})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids

    def test_filter_nested_dot_notation_range(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "metadata": {"author": "alice", "score": 80}})
        search.add_document("d2", {"title": "B", "metadata": {"author": "bob", "score": 60}})
        results = search.search("", filters={"metadata.score": {"$gte": 70}})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids

    # -- List intersection filters --
    def test_filter_list_intersection(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "tags": ["python", "web"]})
        search.add_document("d2", {"title": "B", "tags": ["javascript", "web"]})
        search.add_document("d3", {"title": "C", "tags": ["rust", "systems"]})
        results = search.search("", filters={"tags": ["python"]})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids
        assert "d3" not in ids

    def test_filter_list_intersection_multiple(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "tags": ["python", "web"]})
        search.add_document("d2", {"title": "B", "tags": ["javascript", "web"]})
        search.add_document("d3", {"title": "C", "tags": ["rust", "systems"]})
        results = search.search("", filters={"tags": ["web"]})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" in ids
        assert "d3" not in ids

    # -- SearchResults dict-style access --
    def test_searchresults_getitem(self):
        sr = SearchResults(results=[{"id": "1"}], total=1, page=1, page_size=20)
        assert sr["results"] == [{"id": "1"}]
        assert sr["total"] == 1
        assert sr["page"] == 1
        assert sr["page_size"] == 20

    def test_searchresults_contains(self):
        sr = SearchResults(results=[], total=0)
        assert "results" in sr
        assert "total" in sr
        assert "facets" in sr
        assert "nonexistent" not in sr

    def test_searchresults_keys(self):
        sr = SearchResults(results=[], total=0)
        keys = sr.keys()
        assert "results" in keys
        assert "facets" in keys
        assert "total" in keys
        assert "page" in keys
        assert "page_size" in keys

    # -- Combined range + exact match filters --
    def test_combined_range_and_exact(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "score": 80, "category": "tech"})
        search.add_document("d2", {"title": "B", "score": 60, "category": "tech"})
        search.add_document("d3", {"title": "C", "score": 90, "category": "cooking"})
        results = search.search("", filters={"score": {"$gte": 70}, "category": "tech"})
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids
        assert "d3" not in ids

    def test_combined_multiple_ranges(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "score": 80, "views": 100})
        search.add_document("d2", {"title": "B", "score": 60, "views": 200})
        search.add_document("d3", {"title": "C", "score": 90, "views": 50})
        results = search.search("", filters={
            "score": {"$gte": 70},
            "views": {"$lte": 150},
        })
        ids = [r["id"] for r in results["results"]]
        assert "d1" in ids
        assert "d2" not in ids
        assert "d3" in ids

    def test_combined_in_and_exact(self):
        search = FacetedSearch()
        search.add_document("d1", {"title": "A", "score": 80, "category": "tech"})
        search.add_document("d2", {"title": "B", "score": 60, "category": "tech"})
        search.add_document("d3", {"title": "C", "score": 90, "category": "cooking"})
        results = search.search("", filters={
            "score": {"$in": [60, 90]},
            "category": "tech",
        })
        ids = [r["id"] for r in results["results"]]
        assert "d2" in ids
        assert "d1" not in ids
        assert "d3" not in ids
