"""Test that migrations/base.py properly imports importlib.util (TICKET-55)."""
import ast


def test_importlib_util_imported():
    """migrations/base.py should import importlib.util, not just importlib."""
    source = open("personal_index/migrations/base.py").read()
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    assert "importlib.util" in imports, (
        f"importlib.util not found in imports. Got: {[i for i in imports if 'importlib' in i]}"
    )


def test_importlib_util_runtime():
    """migrations/base.py should be importable without errors."""
    import personal_index.migrations.base
    assert hasattr(personal_index.migrations.base, "BaseMigration")
