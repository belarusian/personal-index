"""Test TICKET-104: Remove unused TYPE_CHECKING import in content_tagger/tagger.py"""

import ast


def test_no_type_checking_import_in_tagger():
    """Verify TYPE_CHECKING is not imported in tagger.py."""
    with open("personal_index/content_tagger/tagger.py") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            names = [alias.name for alias in node.names]
            assert "TYPE_CHECKING" not in names, (
                "TYPE_CHECKING should not be imported in tagger.py"
            )


def test_tagger_module_imports_cleanly():
    """Verify the module still imports correctly after the fix."""
    from personal_index.content_tagger.tagger import ContentTagger, TagResult
    assert ContentTagger is not None
    assert TagResult is not None


def test_tagger_functionality():
    """Verify ContentTagger still works after removing TYPE_CHECKING."""
    from personal_index.content_tagger.tagger import ContentTagger

    tagger = ContentTagger()
    result = tagger.tag("python programming")
    assert result is not None
    assert result.content == "python programming"
