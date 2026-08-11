"""
Codebase visualization tool that generates a single HTML dashboard
showing the state of the personal-index project.

Scans all Python modules, extracts metadata via AST parsing,
runs linting/type-checking/testing tools, and produces a
self-contained HTML dashboard with dark theme.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FunctionInfo:
    """Metadata about a single function / method."""
    name: str
    line: int
    docstring: str = ""
    is_async: bool = False
    is_method: bool = False
    parent_class: str = ""


@dataclass
class ClassInfo:
    """Metadata about a single class."""
    name: str
    line: int
    docstring: str = ""
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Metadata about a single Python module."""
    filepath: str
    module_name: str
    line_count: int = 0
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    docstring: str = ""
    ruff_errors: list[str] = field(default_factory=list)
    ruff_warnings: list[str] = field(default_factory=list)
    mypy_errors: list[str] = field(default_factory=list)
    test_count: int = 0
    status: str = "clean"  # clean | warning | error


@dataclass
class DashboardData:
    """Aggregated data for the HTML dashboard."""
    modules: list[ModuleInfo] = field(default_factory=list)
    total_modules: int = 0
    total_lines: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_tests: int = 0
    total_ruff_errors: int = 0
    total_ruff_warnings: int = 0
    total_mypy_errors: int = 0
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    test_results: str = ""


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _extract_docstring(node: ast.AST) -> str:  # type: ignore[arg-type]  # type: ignore[assignment]
    """Pull the docstring from a function/class/module node."""
    return ast.get_docstring(node) or ""  # type: ignore[arg-type]


def _parse_module(filepath: str) -> ModuleInfo:
    """Parse a single Python file and return ModuleInfo."""
    module_name = _filepath_to_module(filepath)
    info = ModuleInfo(filepath=filepath, module_name=module_name)

    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
    except OSError:
        info.status = "error"
        return info

    info.line_count = max(source.count("\n"), 1)
    info.docstring = ""

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as exc:
        info.ruff_errors.append(f"SyntaxError: {exc}")
        info.status = "error"
        return info

    info.docstring = _extract_docstring(tree)

    # Top-level imports
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                info.imports.append(name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                info.imports.append(f"{module}.{name}" if module else name)

    # Top-level functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = FunctionInfo(
                name=node.name,
                line=node.lineno,
                docstring=_extract_docstring(node),
                is_async=isinstance(node, ast.AsyncFunctionDef),
            )
            info.functions.append(func)

        elif isinstance(node, ast.ClassDef):
            cls = ClassInfo(
                name=node.name,
                line=node.lineno,
                docstring=_extract_docstring(node),
                bases=[_ast_name(b) for b in node.bases],
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method = FunctionInfo(
                        name=item.name,
                        line=item.lineno,
                        docstring=_extract_docstring(item),
                        is_async=isinstance(item, ast.AsyncFunctionDef),
                        is_method=True,
                        parent_class=node.name,
                    )
                    cls.methods.append(method)
            info.classes.append(cls)

    return info


def _ast_name(node: ast.expr) -> str:
    """Convert an AST name / attribute node to a string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_ast_name(node.value)}.{node.attr}"
    return ast.dump(node)


def _filepath_to_module(filepath: str) -> str:
    """Convert a file path like personal_index/api/handlers.py -> personal_index.api.handlers."""
    rel = os.path.relpath(filepath, start=".")
    parts = Path(rel).with_suffix("").parts
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def scan_modules(root: str = "personal_index") -> list[ModuleInfo]:
    """Walk *root* and parse every .py file."""
    modules: list[ModuleInfo] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, fname)
            modules.append(_parse_module(filepath))
    return modules


# ---------------------------------------------------------------------------
# Relationship detection
# ---------------------------------------------------------------------------

def detect_dependencies(modules: list[ModuleInfo]) -> dict[str, list[str]]:
    """Build a module -> [imported modules] map."""
    module_names = {m.module_name for m in modules}
    graph: dict[str, list[str]] = {m.module_name: [] for m in modules}

    for mod in modules:
        for imp in mod.imports:
            # Try to match import against known module names
            for name in module_names:
                if (name == imp or name.endswith(f".{imp}") or imp.endswith(f".{name}")) and name != mod.module_name:
                        graph.setdefault(mod.module_name, []).append(name)
    return graph


# ---------------------------------------------------------------------------
# Tool integration
# ---------------------------------------------------------------------------

def run_ruff(modules: list[ModuleInfo]) -> None:
    """Run ruff check on each module and store results."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--output-format=text", "personal_index/"],
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            # Try to match line to a module
            for mod in modules:
                rel = os.path.relpath(mod.filepath, start=".")
                if rel in line or mod.module_name.replace(".", "/") in line:
                    if "error" in line.lower() or "F" in line or "E" in line:
                        mod.ruff_errors.append(line.strip())
                    else:
                        mod.ruff_warnings.append(line.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Update status
    for mod in modules:
        if mod.ruff_errors:
            mod.status = "error"
        elif mod.ruff_warnings:
            mod.status = "warning"


def run_mypy(modules: list[ModuleInfo]) -> None:
    """Run mypy on each module and store results."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "personal_index/"],
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            for mod in modules:
                rel = os.path.relpath(mod.filepath, start=".")
                if rel in line or mod.module_name.replace(".", "/") in line:
                    mod.mypy_errors.append(line.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    for mod in modules:
        if mod.mypy_errors and mod.status != "error":
            mod.status = "error"


def run_pytest(modules: list[ModuleInfo]) -> str:
    """Run pytest and count tests per module; return summary text."""
    summary = ""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
        summary = result.stdout.strip()
        # Count tests per module by looking at test file names
        for line in summary.splitlines():
            for mod in modules:
                test_name = f"test_{mod.module_name.split('.')[-1]}"
                if test_name in line:
                    mod.test_count += 1
    except (subprocess.TimeoutExpired, FileNotFoundError):
        summary = "pytest could not be run"
    return summary


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _status_color(status: str) -> str:
    return {"clean": "#22c55e", "warning": "#eab308", "error": "#ef4444"}.get(status, "#6b7280")


def _status_bg(status: str) -> str:
    return {"clean": "#166534", "warning": "#854d0e", "error": "#991b1b"}.get(status, "#374151")


def generate_dashboard(data: DashboardData, output_path: str = "personal_index/docs_dashboard.html") -> None:
    """Generate a self-contained HTML dashboard file."""
    # Build module grid rows
    module_rows = ""
    for mod in sorted(data.modules, key=lambda m: m.module_name):
        color = _status_color(mod.status)
        bg = _status_bg(mod.status)
        classes_count = len(mod.classes)
        funcs_count = len(mod.functions)
        methods_count = sum(len(c.methods) for c in mod.classes)
        total_funcs = funcs_count + methods_count
        errors = len(mod.ruff_errors) + len(mod.mypy_errors)
        warnings = len(mod.ruff_warnings)
        module_rows += f"""\
            <div class="module-card" style="border-left: 4px solid {color};">
                <div class="module-header">
                    <span class="module-name">{_escape_html(mod.module_name)}</span>
                    <span class="status-badge" style="background:{bg};color:{color};">{_escape_html(mod.status)}</span>
                </div>
                <div class="module-stats">
                    <span>{mod.line_count} lines</span>
                    <span>{classes_count} classes</span>
                    <span>{total_funcs} functions</span>
                    <span>{mod.test_count} tests</span>
                    <span>{errors} errors</span>
                    <span>{warnings} warnings</span>
                </div>
            </div>
"""

    # Build dependency tree
    dep_tree = ""
    for mod_name in sorted(data.dependency_graph.keys()):
        deps = data.dependency_graph.get(mod_name, [])
        if deps:
            dep_tree += f"<div class='dep-node'><strong>{_escape_html(mod_name)}</strong>\n"
            for dep in sorted(set(deps)):
                dep_tree += f"  <div class='dep-child'>└── {_escape_html(dep)}</div>\n"
            dep_tree += "</div>\n"

    # Build test coverage bars
    test_bars = ""
    max_tests = max((m.test_count for m in data.modules), default=1) or 1
    for mod in sorted(data.modules, key=lambda m: m.test_count, reverse=True):
        if mod.test_count > 0:
            pct = (mod.test_count / max_tests) * 100
            test_bars += f"""\
                <div class="test-bar-row">
                    <span class="test-bar-label">{_escape_html(mod.module_name)}</span>
                    <div class="test-bar-track">
                        <div class="test-bar-fill" style="width:{pct:.0f}%;">{mod.test_count}</div>
                    </div>
                </div>
"""

    # Summary stats
    total_errors = data.total_ruff_errors + data.total_mypy_errors
    total_warnings = data.total_ruff_warnings

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>personal-index Dashboard</title>
<style>
    :root {{
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --bg-card: #1e293b;
        --text-primary: #e2e8f0;
        --text-secondary: #94a3b8;
        --accent: #38bdf8;
        --border: #334155;
        --green: #22c55e;
        --yellow: #eab308;
        --red: #ef4444;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: var(--bg-primary);
        color: var(--text-primary);
        line-height: 1.6;
        padding: 2rem;
    }}
    h1 {{
        font-size: 2rem;
        margin-bottom: 0.5rem;
        color: var(--accent);
    }}
    h2 {{
        font-size: 1.4rem;
        margin: 2rem 0 1rem;
        color: var(--text-primary);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.5rem;
    }}
    .subtitle {{
        color: var(--text-secondary);
        margin-bottom: 2rem;
    }}
    /* Summary stats */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }}
    .stat-card {{
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.25rem;
        text-align: center;
    }}
    .stat-value {{
        font-size: 2rem;
        font-weight: 700;
        color: var(--accent);
    }}
    .stat-label {{
        font-size: 0.85rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }}
    .stat-card.errors .stat-value {{ color: var(--red); }}
    .stat-card.warnings .stat-value {{ color: var(--yellow); }}
    .stat-card.tests .stat-value {{ color: var(--green); }}

    /* Module grid */
    .module-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 0.75rem;
    }}
    .module-card {{
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0.75rem 1rem;
    }}
    .module-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }}
    .module-name {{
        font-family: 'Fira Code', 'Cascadia Code', monospace;
        font-size: 0.9rem;
        color: var(--text-primary);
    }}
    .status-badge {{
        font-size: 0.7rem;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-weight: 600;
        text-transform: uppercase;
    }}
    .module-stats {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }}

    /* Test bars */
    .test-bar-row {{
        display: flex;
        align-items: center;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }}
    .test-bar-label {{
        width: 260px;
        min-width: 260px;
        font-family: monospace;
        color: var(--text-secondary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .test-bar-track {{
        flex: 1;
        background: var(--bg-primary);
        border-radius: 4px;
        height: 22px;
        overflow: hidden;
    }}
    .test-bar-fill {{
        background: var(--green);
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #fff;
        min-width: 24px;
        border-radius: 4px;
    }}

    /* Dependency tree */
    .dep-tree {{
        font-family: 'Fira Code', 'Cascadia Code', monospace;
        font-size: 0.85rem;
        color: var(--text-secondary);
        line-height: 1.8;
    }}
    .dep-node {{ margin-bottom: 0.5rem; }}
    .dep-child {{ padding-left: 1rem; color: var(--text-secondary); }}

    /* Test results */
    .test-results {{
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 1rem;
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--text-secondary);
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
    }}

    /* Footer */
    .footer {{
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border);
        color: var(--text-secondary);
        font-size: 0.8rem;
        text-align: center;
    }}
</style>
</head>
<body>

<h1>personal-index Dashboard</h1>
<p class="subtitle">Codebase visualization &amp; health report</p>

<!-- Summary Stats -->
<h2>Summary Statistics</h2>
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-value">{data.total_modules}</div>
        <div class="stat-label">Modules</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{data.total_lines:,}</div>
        <div class="stat-label">Lines of Code</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{data.total_classes}</div>
        <div class="stat-label">Classes</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{data.total_functions}</div>
        <div class="stat-label">Functions</div>
    </div>
    <div class="stat-card tests">
        <div class="stat-value">{data.total_tests}</div>
        <div class="stat-label">Tests</div>
    </div>
    <div class="stat-card warnings">
        <div class="stat-value">{total_warnings}</div>
        <div class="stat-label">Warnings</div>
    </div>
    <div class="stat-card errors">
        <div class="stat-value">{total_errors}</div>
        <div class="stat-label">Errors</div>
    </div>
</div>

<!-- Module Map -->
<h2>Module Map</h2>
<div class="module-grid">
{module_rows}
</div>

<!-- Test Coverage -->
<h2>Test Coverage</h2>
{test_bars if test_bars else '<p style="color:var(--text-secondary)">No test data available.</p>'}

<!-- Dependency Graph -->
<h2>Dependency Graph</h2>
<div class="dep-tree">
{dep_tree if dep_tree else '<p>No cross-module dependencies detected.</p>'}
</div>

<!-- Test Results -->
<h2>Test Results</h2>
<div class="test-results">{_escape_html(data.test_results) if data.test_results else 'No test results available.'}</div>

<div class="footer">
    Generated by personal_index.docs_generator &mdash; {data.total_modules} modules analyzed
</div>

</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate(root: str = "personal_index", output: str = "personal_index/docs_dashboard.html") -> str:
    """Full pipeline: scan → lint → type-check → test → generate HTML."""
    print(f"[docs_generator] Scanning modules in {root} ...")
    modules = scan_modules(root)
    print(f"[docs_generator] Found {len(modules)} modules")

    print("[docs_generator] Running ruff check ...")
    run_ruff(modules)

    print("[docs_generator] Running mypy ...")
    run_mypy(modules)

    print("[docs_generator] Running pytest ...")
    test_summary = run_pytest(modules)

    # Build dependency graph
    dep_graph = detect_dependencies(modules)

    # Aggregate
    data = DashboardData(
        modules=modules,
        total_modules=len(modules),
        total_lines=sum(m.line_count for m in modules),
        total_classes=sum(len(m.classes) for m in modules),
        total_functions=sum(len(m.functions) + sum(len(c.methods) for c in m.classes) for m in modules),
        total_tests=sum(m.test_count for m in modules),
        total_ruff_errors=sum(len(m.ruff_errors) for m in modules),
        total_ruff_warnings=sum(len(m.ruff_warnings) for m in modules),
        total_mypy_errors=sum(len(m.mypy_errors) for m in modules),
        dependency_graph=dep_graph,
        test_results=test_summary,
    )

    print(f"[docs_generator] Generating dashboard → {output}")
    generate_dashboard(data, output)
    print(f"[docs_generator] Done. {data.total_modules} modules, {data.total_lines:,} lines, "
          f"{data.total_ruff_errors + data.total_mypy_errors} errors, "
          f"{data.total_ruff_warnings} warnings")
    return output


if __name__ == "__main__":
    generate()
