"""Tests for content diff and change detection."""

from personal_index.content_diff.changes import (
    Change,
    ChangeType,
    ContentDiff,
)


class TestChange:
    def test_added(self):
        c = Change(field="title", change_type=ChangeType.ADDED, new_value="New Title")
        assert c.field == "title"
        assert c.old_value is None
        assert c.new_value == "New Title"

    def test_removed(self):
        c = Change(field="title", change_type=ChangeType.REMOVED, old_value="Old Title")
        assert c.old_value == "Old Title"
        assert c.new_value is None

    def test_modified(self):
        c = Change(field="title", change_type=ChangeType.MODIFIED, old_value="Old", new_value="New")
        assert c.old_value == "Old"
        assert c.new_value == "New"


class TestContentDiff:
    def test_no_changes(self):
        d = ContentDiff.compute({"id": "1", "title": "A"}, {"id": "1", "title": "A"})
        assert d.has_changes is False
        assert d.change_count == 0
        assert d.summary == "No changes"

    def test_added_field(self):
        d = ContentDiff.compute({"id": "1"}, {"id": "1", "title": "New"})
        assert d.has_changes is True
        assert d.change_count == 1
        assert d.changes[0].change_type == ChangeType.ADDED

    def test_removed_field(self):
        d = ContentDiff.compute({"id": "1", "title": "Old"}, {"id": "1"})
        assert d.changes[0].change_type == ChangeType.REMOVED
        assert d.changes[0].old_value == "Old"

    def test_modified_field(self):
        d = ContentDiff.compute({"id": "1", "title": "Old"}, {"id": "1", "title": "New"})
        assert d.changes[0].change_type == ChangeType.MODIFIED
        assert d.changes[0].old_value == "Old"
        assert d.changes[0].new_value == "New"

    def test_multiple_changes(self):
        old = {"id": "1", "title": "A", "body": "B"}
        new = {"id": "1", "title": "C", "body": "B", "tags": ["x"]}
        d = ContentDiff.compute(old, new)
        assert d.change_count == 2

    def test_summary_text(self):
        old = {"id": "1", "a": 1, "b": 2}
        new = {"id": "1", "a": 10, "c": 3}
        d = ContentDiff.compute(old, new)
        assert "1 removed" in d.summary
        assert "1 added" in d.summary

    def test_get_changes_by_type(self):
        d = ContentDiff.compute(
            {"id": "1", "a": 1, "b": 2},
            {"id": "1", "a": 10, "c": 3}
        )
        modified = d.get_changes_by_type(ChangeType.MODIFIED)
        assert len(modified) == 1
        removed = d.get_changes_by_type(ChangeType.REMOVED)
        assert len(removed) == 1

    def test_id_field_custom(self):
        d = ContentDiff.compute({"uid": "x1"}, {"uid": "x2"}, id_field="uid")
        assert d.item_id == "x2"

    def test_id_unknown(self):
        d = ContentDiff.compute({}, {})
        assert d.item_id == "unknown"

    def test_summary_no_changes(self):
        assert ContentDiff._summary_text([]) == "No changes"

    def test_summary_multiple_types(self):
        changes = [
            Change("a", ChangeType.ADDED, new_value=1),
            Change("b", ChangeType.REMOVED, old_value=2),
            Change("c", ChangeType.MODIFIED, old_value=3, new_value=4),
        ]
        s = ContentDiff._summary_text(changes)
        assert "1 added" in s
        assert "1 removed" in s
        assert "1 modified" in s

    def test_unchanged_field_returns_none(self):
        result = ContentDiff._diff_field("a", {"a": 1}, {"a": 1})
        assert result is None

    def test_diff_field_added(self):
        c = ContentDiff._diff_field("a", {}, {"a": 1})
        assert c is not None
        assert c.change_type == ChangeType.ADDED

    def test_diff_field_removed(self):
        c = ContentDiff._diff_field("a", {"a": 1}, {})
        assert c is not None
        assert c.change_type == ChangeType.REMOVED


class TestComputeDocstring535:
    """Pin the ContentDiff.compute exact contract (TICKET-535)."""

    def test_docstring_states_exact_contract(self):
        doc = ContentDiff.compute.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "item_id" in doc
        assert "union" in doc
        assert "sorted" in doc
        assert "ADDED" in doc
        assert "REMOVED" in doc
        assert "MODIFIED" in doc
        assert "No changes" in doc

    def test_item_id_fallback_chain(self):
        # new item wins
        assert ContentDiff.compute({"id": "1"}, {"id": "2"}).item_id == "2"
        # old item fallback
        assert ContentDiff.compute({"id": "1"}, {}).item_id == "1"
        # literal "unknown" when neither has the id field
        assert ContentDiff.compute({}, {}).item_id == "unknown"
        # custom id_field
        assert (
            ContentDiff.compute({"uid": "x1"}, {"uid": "x2"}, id_field="uid").item_id
            == "x2"
        )

    def test_summary_order_and_no_changes(self):
        d = ContentDiff.compute(
            {"id": "1", "a": "x", "b": "y", "c": "z"},
            {"id": "1", "b": "Y", "d": "w"},
        )
        assert d.summary == "1 added, 2 removed, 1 modified"
        assert ContentDiff.compute({"id": "1"}, {"id": "1"}).summary == "No changes"
