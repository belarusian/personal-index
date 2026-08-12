"""Test TICKET-111: Fix accessing private _bookmarks attribute in export.py"""



def test_no_private_bookmarks_access_in_export():
    """Verify export.py does not access _bookmarks private attribute."""
    with open("personal_index/export.py") as f:
        source = f.read()
    assert "_bookmarks" not in source, (
        "export.py should not access private _bookmarks attribute"
    )


def test_export_filtered_works():
    """Verify export_filtered still works after removing _bookmarks access."""
    from personal_index.bookmarks import Bookmark, BookmarkManager
    from personal_index.export import Exporter

    manager = BookmarkManager()
    manager.add(Bookmark(url="http://a.com", title="A", category="tech", tags=["python"]))
    manager.add(Bookmark(url="http://b.com", title="B", category="science", tags=["biology"]))
    manager.add(Bookmark(url="http://c.com", title="C", category="tech", tags=["rust"]))

    exporter = Exporter(manager=manager)

    # Filter by category
    result = exporter.export_filtered("json", category="tech")
    assert result is not None
    assert "A" in result
    assert "C" in result
    assert "B" not in result

    # Filter by tag
    result = exporter.export_filtered("json", tag="python")
    assert result is not None
    assert "A" in result
    assert "B" not in result
    assert "C" not in result

    # Filter by favorites
    manager.toggle_favorite("http://a.com")
    result = exporter.export_filtered("json", favorites_only=True)
    assert result is not None
    assert "A" in result
    assert "B" not in result


def test_export_filtered_does_not_mutate_manager():
    """Verify export_filtered does not mutate the original manager."""
    from personal_index.bookmarks import Bookmark, BookmarkManager
    from personal_index.export import Exporter

    manager = BookmarkManager()
    manager.add(Bookmark(url="http://a.com", title="A", category="tech"))
    manager.add(Bookmark(url="http://b.com", title="B", category="science"))

    exporter = Exporter(manager=manager)
    original_count = manager.count()

    exporter.export_filtered("json", category="tech")

    # Manager should be unchanged
    assert manager.count() == original_count
    assert manager.get("http://a.com") is not None
    assert manager.get("http://b.com") is not None
