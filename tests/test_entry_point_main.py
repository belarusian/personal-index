"""Pinning test for ARCH-103: the console-script entry point target resolves.

The `personal-index` console script is declared in two packaging files.
Both must name a symbol that actually exists in `personal_index.cli`.
`pyproject.toml` `[project.scripts]` and `setup.py` `entry_points`
both target `personal_index.cli:main`. The guard path: a regression to a
non-existent symbol (the old `cli`) makes the import fail.
"""

import click

from personal_index.cli import main


def test_entry_point_target_resolves_to_click_group():
    """`main` exists in personal_index.cli and is the click group."""
    assert isinstance(main, click.Group)
    assert main.name == "main"


def test_setup_py_entry_point_targets_main():
    """setup.py's console_scripts entry names a symbol that resolves."""
    import ast

    with open("setup.py") as f:
        tree = ast.parse(f.read())

    entry = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, val in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "console_scripts"
                    and isinstance(val, ast.List)
                ):
                    for elt in val.elts:
                        if isinstance(elt, ast.Constant):
                            entry = elt.value
    assert entry is not None
    target = entry.split("=", 1)[1]
    module, symbol = target.split(":")
    assert module == "personal_index.cli"
    # The named symbol must actually exist in the module (guard path).
    import importlib

    mod = importlib.import_module(module)
    assert hasattr(mod, symbol), f"entry point target {target} does not resolve"
