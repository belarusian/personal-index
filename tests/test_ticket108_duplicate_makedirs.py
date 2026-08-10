"""Test TICKET-108: Remove duplicate os.makedirs call in interests.py"""

import ast


def test_no_duplicate_makedirs_in_interests():
    """Verify there is only one os.makedirs call in _save method."""
    with open("personal_index/interests.py") as f:
        source = f.read()
    tree = ast.parse(source)
    # Count os.makedirs calls in the entire file
    makedirs_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "makedirs":
                makedirs_count += 1
    assert makedirs_count == 1, (
        f"Expected 1 os.makedirs call, found {makedirs_count}"
    )


def test_interest_store_save_works(tmp_path):
    """Verify InterestStore._save still works after removing duplicate."""
    from personal_index.interests import InterestStore
    from personal_index.models import Interest

    store_path = str(tmp_path / "subdir" / "interests.json")
    store = InterestStore(store_path=store_path)
    interest = Interest(name="test", keywords=["python"], topics=["tech"])
    store.add(interest)
    assert store.get("test") is not None
    # Verify file was created
    assert (tmp_path / "subdir" / "interests.json").exists()
