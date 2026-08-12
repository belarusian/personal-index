"""Tests for search_facets module - filterable search dimensions."""


from personal_index.search_facets.facet import Facet, FacetType, FacetValue
from personal_index.search_facets.facet_builder import FacetBuilder
from personal_index.search_facets.faceted_search import FacetedSearch

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
