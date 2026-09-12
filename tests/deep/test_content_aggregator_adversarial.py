import pytest
from personal_index.content_aggregator import ContentAggregator

def make_agg():
    return ContentAggregator()

def test_init_empty():
    agg = make_agg()
    assert agg.source_count == 0
    assert agg.total_items == 0
    assert agg.get_source_names() == []

def test_add_source_empty_name():
    agg = make_agg()
    agg.add_source("", [{"id": 1}])
    assert "" in agg.get_source_names()
    assert agg.get_source("") == [{"id": 1}]

def test_add_source_whitespace_name():
    agg = make_agg()
    agg.add_source("   ", [{"id": 2}])
    assert "   " in agg.get_source_names()

def test_add_source_unicode_name():
    agg = make_agg()
    agg.add_source("源🔥", [{"id": 3}])
    assert "源🔥" in agg.get_source_names()

def test_add_source_none_items():
    agg = make_agg()
    with pytest.raises(TypeError):
        agg.add_source("s", None)

def test_add_source_empty_list():
    agg = make_agg()
    agg.add_source("s", [])
    assert agg.total_items == 0

def test_get_source_missing():
    agg = make_agg()
    assert agg.get_source("missing") == []

def test_filter_by_source_missing():
    agg = make_agg()
    assert agg.filter_by_source("missing") == []

def test_merge_all_empty():
    agg = make_agg()
    assert agg.merge_all() == []

def test_merge_all_no_dedup():
    agg = make_agg()
    agg.add_source("a", [{"id": 1}, {"id": 1}])
    agg.add_source("b", [{"id": 1}])
    merged = agg.merge_all(deduplicate=False)
    assert len(merged) == 3

def test_merge_all_dedup_by_id():
    agg = make_agg()
    agg.add_source("a", [{"id": "x", "title": "A"}])
    agg.add_source("b", [{"id": "x", "title": "B"}])
    merged = agg.merge_all()
    assert len(merged) == 1
    assert merged[0]["title"] == "A"

def test_merge_all_dedup_by_title_fallback():
    agg = make_agg()
    agg.add_source("a", [{"title": "t1"}])
    agg.add_source("b", [{"title": "t1"}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_dedup_keep_first_order():
    agg = make_agg()
    agg.add_source("first", [{"id": 1}])
    agg.add_source("second", [{"id": 2}])
    merged = agg.merge_all()
    assert [i["id"] for i in merged] == [1, 2]

def test_merge_all_id_none_fallback_title():
    agg = make_agg()
    agg.add_source("a", [{"id": None, "title": "T"}])
    agg.add_source("b", [{"id": None, "title": "T"}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_id_empty_string():
    agg = make_agg()
    agg.add_source("a", [{"id": "", "title": "A"}])
    agg.add_source("b", [{"id": "", "title": "B"}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_id_zero():
    agg = make_agg()
    agg.add_source("a", [{"id": 0, "title": "A"}])
    agg.add_source("b", [{"id": 0, "title": "B"}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_whitespace_key():
    agg = make_agg()
    agg.add_source("a", [{"id": "  "}])
    agg.add_source("b", [{"id": "  "}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_unicode_key():
    agg = make_agg()
    agg.add_source("a", [{"id": "🔥"}])
    agg.add_source("b", [{"id": "🔥"}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_missing_id_title():
    agg = make_agg()
    agg.add_source("a", [{}])
    agg.add_source("b", [{}])
    merged = agg.merge_all()
    assert len(merged) == 1

def test_merge_all_idempotence():
    agg = make_agg()
    agg.add_source("a", [{"id": 1}])
    m1 = agg.merge_all()
    m2 = agg.merge_all()
    assert m1 == m2

def test_merge_all_roundtrip_source_order():
    agg = make_agg()
    agg.add_source("z", [{"id": 3}])
    agg.add_source("a", [{"id": 1}])
    agg.add_source("m", [{"id": 2}])
    merged = agg.merge_all(deduplicate=False)
    assert [i["id"] for i in merged] == [3, 1, 2]

def test_clear_source_exists():
    agg = make_agg()
    agg.add_source("s", [{"id": 1}])
    assert agg.clear_source("s") is True
    assert agg.source_count == 0

def test_clear_source_missing():
    agg = make_agg()
    assert agg.clear_source("nope") is False

def test_clear_all():
    agg = make_agg()
    agg.add_source("a", [{"id": 1}])
    agg.add_source("b", [{"id": 2}])
    agg.clear_all()
    assert agg.source_count == 0
    assert agg.total_items == 0

def test_total_items_multiple():
    agg = make_agg()
    agg.add_source("a", [{"id": 1}, {"id": 2}])
    agg.add_source("b", [{"id": 3}])
    assert agg.total_items == 3

def test_source_count():
    agg = make_agg()
    agg.add_source("a", [])
    agg.add_source("b", [])
    assert agg.source_count == 2

def test_add_source_overwrite():
    agg = make_agg()
    agg.add_source("s", [{"id": 1}])
    agg.add_source("s", [{"id": 2}])
    assert agg.get_source("s") == [{"id": 2}]
    assert agg.total_items == 1

def test_get_source_names_order():
    agg = make_agg()
    agg.add_source("b", [])
    agg.add_source("a", [])
    names = agg.get_source_names()
    assert set(names) == {"a", "b"}
