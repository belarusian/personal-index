"""Tests for TICKET-64: no f-strings without placeholders (F541)."""

import ast
import pathlib


def _find_fstring_violations(tree: ast.AST):
    """Find f-string nodes that have no interpolation placeholders.

    Skips nested JoinedStr nodes that are format specs of FormattedValue,
    since those are not top-level f-strings.
    """
    # First, collect all JoinedStr nodes that are format specs (nested)
    format_spec_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FormattedValue) and node.format_spec and isinstance(node.format_spec, ast.JoinedStr):
            format_spec_lines.add(id(node.format_spec))

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            # Skip if this is a nested format spec
            if id(node) in format_spec_lines:
                continue

            has_interpolation = False
            for value in node.values:
                if isinstance(value, ast.FormattedValue):
                    has_interpolation = True
                    break
            if not has_interpolation:
                violations.append(node.lineno)
    return violations


def test_no_fstrings_without_placeholders():
    """Ensure no f-strings exist without {} placeholders in cli.py."""
    cli_path = pathlib.Path("personal_index/cli.py")
    source = cli_path.read_text()
    tree = ast.parse(source)

    violations = _find_fstring_violations(tree)

    assert not violations, (
        f"f-strings without placeholders found at lines: {violations}"
    )
