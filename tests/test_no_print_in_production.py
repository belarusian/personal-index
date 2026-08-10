"""Tests for TICKET-65: no print() statements in production code."""

import ast
import pathlib


def test_no_print_in_notifications():
    """Ensure no print() calls exist in personal_index/notifications.py."""
    path = pathlib.Path("personal_index/notifications.py")
    source = path.read_text()
    tree = ast.parse(source)

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Check for bare print() or print(...)
            if isinstance(func, ast.Name) and func.id == "print":
                violations.append(node.lineno)

    assert not violations, (
        f"print() calls found at lines: {violations}"
    )
