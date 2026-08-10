"""Test TICKET-97: Module docstrings are at the top of files."""

import ast


def _get_module_docstring(tree: ast.Module) -> str | None:
    """Get module docstring, handling from __future__ imports."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue  # Skip __future__ imports
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
        break  # Stop at first non-__future__ statement
    return None


def test_url_classifier_has_module_docstring():
    """url_classifier.py should have a module docstring at the top."""
    with open('personal_index/url_classifier.py', 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    docstring = _get_module_docstring(tree)
    assert docstring is not None, "url_classifier.py should have a module docstring"
    assert "URL classification" in docstring or "categorizing" in docstring.lower()


def test_url_classifier_docstring_at_top():
    """url_classifier.py module docstring should be near the top, not at the end."""
    with open('personal_index/url_classifier.py', 'r') as f:
        lines = f.readlines()
    # Docstring should be within first 10 lines
    found_docstring = False
    for i, line in enumerate(lines[:10]):
        if '"""' in line and 'URL classification' in line:
            found_docstring = True
            break
    assert found_docstring, "Module docstring should be within first 10 lines"


def test_validator_has_module_docstring():
    """validator.py should have a module docstring at the top."""
    with open('personal_index/validator.py', 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    docstring = _get_module_docstring(tree)
    assert docstring is not None, "validator.py should have a module docstring"
    assert "URL" in docstring or "validation" in docstring.lower()


def test_validator_docstring_at_top():
    """validator.py module docstring should be near the top, not at the end."""
    with open('personal_index/validator.py', 'r') as f:
        lines = f.readlines()
    # Docstring should be within first 10 lines
    found_docstring = False
    for i, line in enumerate(lines[:10]):
        if '"""' in line and ('URL' in line or 'validation' in line.lower()):
            found_docstring = True
            break
    assert found_docstring, "Module docstring should be within first 10 lines"


def test_url_classifier_no_misplaced_docstring_at_end():
    """url_classifier.py should not have a docstring at the end of the file."""
    with open('personal_index/url_classifier.py', 'r') as f:
        content = f.read()
    # The last non-empty line should not be a docstring
    lines = [l for l in content.split('\n') if l.strip()]
    assert not lines[-1].startswith('"""'), "No docstring should be at the end of the file"


def test_validator_no_misplaced_docstring_at_end():
    """validator.py should not have a docstring at the end of the file."""
    with open('personal_index/validator.py', 'r') as f:
        content = f.read()
    # The last non-empty line should not be a docstring
    lines = [l for l in content.split('\n') if l.strip()]
    assert not lines[-1].startswith('"""'), "No docstring should be at the end of the file"
