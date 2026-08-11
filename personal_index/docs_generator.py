"""
Codebase visualization tool that generates a single HTML dashboard
showing the state of the personal-index project.

Scans all Python modules, extracts metadata via AST parsing,
runs linting/type-checking/testing tools, and produces a
self-contained HTML dashboard with dark terminal aesthetic.
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
class CommitInfo:
    """Metadata about a single git commit."""
    sha_short: str
    message: str
    author: str
    date: str


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
    commits: list[CommitInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _extract_docstring(node: ast.AST) -> str:
    """Pull the docstring from a function/class/module node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        return ast.get_docstring(node) or ""
    return ""


def _ast_name(node: ast.AST) -> str:
    """Get the name string from an AST Name/Attribute node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_ast_name(node.value)}.{node.attr}"
    return "?"


def _filepath_to_module(filepath: str) -> str:
    """Convert a file path to a dotted module name."""
    parts = Path(filepath).with_suffix("").parts
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Module scanning
# ---------------------------------------------------------------------------

def scan_modules(root: str) -> list[ModuleInfo]:
    """Walk the directory tree and parse every .py file."""
    modules: list[ModuleInfo] = []
    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, fname)
            modules.append(_parse_module(filepath))
    return modules


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

    # Count test functions
    for func in info.functions:
        if func.name.startswith("test_"):
            info.test_count += 1
    for cls in info.classes:
        for method in cls.methods:
            if method.name.startswith("test_"):
                info.test_count += 1

    return info


# ---------------------------------------------------------------------------
# Linting / type-checking / testing
# ---------------------------------------------------------------------------

def run_ruff(modules: list[ModuleInfo]) -> None:
    """Run ruff check and distribute results to modules."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--output-format=text", "."],
            capture_output=True, text=True, timeout=60, check=False,
        )
        for line in (result.stdout + result.stderr).splitlines():
            line = line.strip()
            if not line:
                continue
            # Try to match a file path
            for mod in modules:
                if mod.filepath in line:
                    if "error" in line.lower() or "F" in line or "E" in line:
                        mod.ruff_errors.append(line)
                    else:
                        mod.ruff_warnings.append(line)
                    break
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    for mod in modules:
        if mod.ruff_errors:
            mod.status = "error"
        elif mod.ruff_warnings:
            mod.status = "warning"


def run_mypy(modules: list[ModuleInfo]) -> None:
    """Run mypy and distribute results to modules."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "."],
            capture_output=True, text=True, timeout=120, check=False,
        )
        for line in (result.stdout + result.stderr).splitlines():
            line = line.strip()
            if not line:
                continue
            for mod in modules:
                if mod.filepath in line:
                    mod.mypy_errors.append(line)
                    break
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    for mod in modules:
        if mod.mypy_errors:
            mod.status = "error"


def run_pytest(modules: list[ModuleInfo]) -> str:
    """Run pytest and count tests per module."""
    summary = ""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        summary = result.stdout + result.stderr
        # Try to attribute tests to modules from output
        for line in summary.splitlines():
            for mod in modules:
                if (mod.filepath.replace("/", ".") in line or mod.module_name in line) and ("PASSED" in line or "passed" in line):
                    mod.test_count = max(mod.test_count, 1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        summary = "pytest could not be run: timed out or not available."
    return summary


# ---------------------------------------------------------------------------
# Dependency detection
# ---------------------------------------------------------------------------

def detect_dependencies(modules: list[ModuleInfo]) -> dict[str, list[str]]:
    """Build a dependency graph: module -> list of modules it imports."""
    module_names = {m.module_name for m in modules}
    graph: dict[str, list[str]] = {}
    for mod in modules:
        deps: list[str] = []
        for imp in mod.imports:
            # Check if import matches any known module (prefix match)
            for name in module_names:
                if (name == imp or name.startswith(imp + ".") or imp.startswith(name + ".")) and name != mod.module_name:
                    deps.append(name)
        graph[mod.module_name] = sorted(set(deps))
    return graph


# ---------------------------------------------------------------------------
# Git log
# ---------------------------------------------------------------------------

def fetch_recent_commits(n: int = 20) -> list[CommitInfo]:
    """Fetch the last N commits from git log."""
    commits: list[CommitInfo] = []
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--format=%h|%s|%an|%ad", "--date=short"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(CommitInfo(
                    sha_short=parts[0].strip(),
                    message=parts[1].strip(),
                    author=parts[2].strip(),
                    date=parts[3].strip(),
                ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return commits


# ---------------------------------------------------------------------------
# HTML generation — dark terminal aesthetic
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def _status_color(status: str) -> str:
    """Return color for module status."""
    if status == "error":
        return "#ef4444"
    elif status == "warning":
        return "#eab308"
    elif status == "clean":
        return "#22c55e"
    return "#6b7280"

def _status_bg(status: str) -> str:
    """Return background color for module status."""
    if status == "error":
        return "#991b1b"
    elif status == "warning":
        return "#854d0e"
    elif status == "clean":
        return "#166534"
    return "#374151"


def _status_indicator(status: str) -> str:
    """Return a status indicator character."""
    if status == "error":
        return "ERR"
    elif status == "warning":
        return "WRN"
    return "OK"


def generate_dashboard(data: DashboardData, output_path: str) -> None:
    """Generate the dark terminal-style HTML dashboard."""

    total_errors = data.total_ruff_errors + data.total_mypy_errors
    total_warnings = data.total_ruff_warnings

    # ---- MODULE MAP rows ----
    module_rows = ""
    for mod in sorted(data.modules, key=lambda m: m.module_name):
        color = _status_color(mod.status)
        indicator = _status_indicator(mod.status)
        class_count = len(mod.classes)
        func_count = len(mod.functions) + sum(len(c.methods) for c in mod.classes)
        module_rows += f"""
    <div class="mod-card" style="border-color: {color};">
        <div class="mod-header">
            <span class="mod-name">{_escape_html(mod.module_name)}</span>
            <span class="mod-status" style="color: {color};">[{indicator}]</span>
        </div>
        <div class="mod-meta">
            <span>CLASSES: {class_count}</span>
            <span>FUNCS: {func_count}</span>
            <span>LINES: {mod.line_count}</span>
            <span>TESTS: {mod.test_count}</span>
        </div>
    </div>"""

    # ---- DEPENDENCY GRAPH (text tree) ----
    dep_tree = ""
    if data.dependency_graph:
        for mod_name, deps in sorted(data.dependency_graph.items()):
            dep_tree += f'<div class="dep-node"><span class="dep-module">{_escape_html(mod_name)}</span></div>\n'
            for dep in deps:
                dep_tree += f'<div class="dep-child">├── {_escape_html(dep)}</div>\n'
    else:
        dep_tree = '<div class="dep-node">No cross-module dependencies detected.</div>'

    # ---- TEST COVERAGE bar chart (sorted by count desc) ----
    test_bars = ""
    sorted_by_tests = sorted(data.modules, key=lambda m: m.test_count, reverse=True)
    max_tests = max((m.test_count for m in sorted_by_tests), default=1)
    if max_tests == 0:
        max_tests = 1
    for mod in sorted_by_tests:
        bar_width = int((mod.test_count / max_tests) * 100)
        test_bars += f"""
    <div class="test-bar-row">
        <span class="test-bar-label">{_escape_html(mod.module_name)}</span>
        <div class="test-bar-track">
            <div class="test-bar-fill" style="width: {bar_width}%;"></div>
        </div>
        <span class="test-bar-count">{mod.test_count}</span>
    </div>"""

    # ---- RECENT COMMITS ----
    commit_rows = ""
    for c in data.commits:
        commit_rows += f"""
    <div class="commit-row">
        <span class="commit-sha">{_escape_html(c.sha_short)}</span>
        <span class="commit-msg">{_escape_html(c.message)}</span>
        <span class="commit-author">{_escape_html(c.author)}</span>
        <span class="commit-date">{_escape_html(c.date)}</span>
    </div>"""

    # ---- HEAT MAP (sorted by errors+warnings desc) ----
    heat_rows = ""
    sorted_by_issues = sorted(data.modules, key=lambda m: len(m.ruff_errors) + len(m.mypy_errors) + len(m.ruff_warnings), reverse=True)
    for mod in sorted_by_issues:
        err_count = len(mod.ruff_errors) + len(mod.mypy_errors)
        warn_count = len(mod.ruff_warnings)
        total_issues = err_count + warn_count
        if total_issues == 0:
            heat_color = "#86f7ad"
            heat_intensity = 0
        elif total_issues <= 2:
            heat_color = "#f0a030"
            heat_intensity = 30
        elif total_issues <= 5:
            heat_color = "#e06030"
            heat_intensity = 60
        else:
            heat_color = "#ff2020"
            heat_intensity = 100
        heat_rows += f"""
    <div class="heat-row">
        <div class="heat-cell" style="background: {heat_color}; opacity: {0.2 + heat_intensity / 100};"></div>
        <span class="heat-name">{_escape_html(mod.module_name)}</span>
        <span class="heat-errs" style="color: {heat_color};">E:{err_count} W:{warn_count}</span>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>personal-index // TERMINAL DASHBOARD</title>
<style>
/* ============================================================
   DARK TERMINAL AESTHETIC
   Background: #010403 | Text: #86f7ad | Font: Courier New
   Scanline overlay + vignette effect
   ============================================================ */

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html, body {{
    background: #010403;
    color: #86f7ad;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    line-height: 1.5;
    min-height: 100vh;
    overflow-x: hidden;
}}

/* Scanline overlay */
body::before {{
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 0, 0, 0.15) 2px,
        rgba(0, 0, 0, 0.15) 4px
    );
    pointer-events: none;
    z-index: 9999;
}}

/* Vignette effect */
body::after {{
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(
        ellipse at center,
        transparent 50%,
        rgba(1, 4, 3, 0.7) 100%
    );
    pointer-events: none;
    z-index: 9998;
}}

/* CRT flicker animation */
@keyframes flicker {{
    0%   {{ opacity: 0.97; }}
    5%   {{ opacity: 1.0; }}
    10%  {{ opacity: 0.98; }}
    15%  {{ opacity: 1.0; }}
    50%  {{ opacity: 0.99; }}
    80%  {{ opacity: 1.0; }}
    100% {{ opacity: 0.97; }}
}}

.dashboard {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    animation: flicker 4s infinite;
    position: relative;
    z-index: 1;
}}

/* ---- HEADER ---- */
.header {{
    border-bottom: 2px solid #86f7ad;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}}

.header h1 {{
    font-size: 1.6rem;
    font-weight: 400;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #86f7ad;
    text-shadow: 0 0 10px rgba(134, 247, 173, 0.5);
}}

.header .prompt {{
    color: #5a9e7a;
    font-size: 0.85rem;
    margin-top: 0.5rem;
}}

.header .prompt::before {{
    content: "> ";
    color: #86f7ad;
}}

/* ---- SECTION HEADERS ---- */
.section {{
    margin-bottom: 2.5rem;
}}

.section-title {{
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #86f7ad;
    border-bottom: 1px solid #1a3a2a;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
    text-shadow: 0 0 8px rgba(134, 247, 173, 0.3);
}}

.section-title::before {{
    content: "## ";
    color: #5a9e7a;
}}

/* ---- SURFACE STATS ---- */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
}}

.stat-card {{
    border: 1px solid #1a3a2a;
    padding: 0.75rem;
    text-align: center;
    background: rgba(134, 247, 173, 0.02);
}}

.stat-value {{
    font-size: 1.8rem;
    color: #86f7ad;
    text-shadow: 0 0 12px rgba(134, 247, 173, 0.4);
    font-weight: 400;
}}

.stat-label {{
    font-size: 0.7rem;
    color: #5a9e7a;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 0.25rem;
}}

.stat-card.warn .stat-value {{
    color: #f0a030;
    text-shadow: 0 0 12px rgba(240, 160, 48, 0.4);
}}

.stat-card.err .stat-value {{
    color: #ff4444;
    text-shadow: 0 0 12px rgba(255, 68, 68, 0.4);
}}

/* ---- MODULE MAP ---- */
.module-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.6rem;
}}

.mod-card {{
    border: 1px solid #1a3a2a;
    padding: 0.6rem 0.8rem;
    background: rgba(134, 247, 173, 0.015);
    transition: background 0.2s;
}}

.mod-card:hover {{
    background: rgba(134, 247, 173, 0.05);
}}

.mod-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.3rem;
}}

.mod-name {{
    font-size: 0.85rem;
    color: #86f7ad;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 70%;
}}

.mod-status {{
    font-size: 0.7rem;
    font-weight: 400;
    letter-spacing: 1px;
}}

.mod-meta {{
    display: flex;
    gap: 0.8rem;
    font-size: 0.7rem;
    color: #5a9e7a;
}}

.mod-meta span::before {{
    color: #3a6e5a;
}}

/* ---- DEPENDENCY GRAPH ---- */
.dep-tree {{
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.82rem;
    color: #5a9e7a;
    line-height: 1.7;
    padding: 0.5rem;
    border: 1px solid #1a3a2a;
    background: rgba(0, 0, 0, 0.3);
    max-height: 400px;
    overflow-y: auto;
}}

.dep-node {{
    margin-bottom: 0.3rem;
}}

.dep-module {{
    color: #86f7ad;
}}

.dep-child {{
    padding-left: 1.2rem;
    color: #4a8e6a;
}}

/* ---- TEST COVERAGE ---- */
.test-bar-row {{
    display: flex;
    align-items: center;
    margin-bottom: 0.35rem;
    font-size: 0.8rem;
}}

.test-bar-label {{
    width: 220px;
    min-width: 220px;
    color: #5a9e7a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: right;
    padding-right: 0.75rem;
}}

.test-bar-track {{
    flex: 1;
    height: 14px;
    background: #0a1a12;
    border: 1px solid #1a3a2a;
    margin-right: 0.5rem;
}}

.test-bar-fill {{
    height: 100%;
    background: #86f7ad;
    box-shadow: 0 0 6px rgba(134, 247, 173, 0.3);
    transition: width 0.3s;
}}

.test-bar-count {{
    width: 30px;
    text-align: right;
    color: #86f7ad;
    font-size: 0.75rem;
}}

/* ---- RECENT COMMITS ---- */
.commit-list {{
    border: 1px solid #1a3a2a;
    background: rgba(0, 0, 0, 0.3);
    max-height: 400px;
    overflow-y: auto;
}}

.commit-row {{
    display: flex;
    padding: 0.35rem 0.75rem;
    font-size: 0.78rem;
    border-bottom: 1px solid #0a1a12;
    gap: 0.75rem;
}}

.commit-row:hover {{
    background: rgba(134, 247, 173, 0.03);
}}

.commit-sha {{
    color: #5a9e7a;
    min-width: 70px;
}}

.commit-msg {{
    flex: 1;
    color: #86f7ad;
}}

.commit-author {{
    color: #4a8e6a;
    min-width: 100px;
}}

.commit-date {{
    color: #3a6e5a;
    min-width: 80px;
}}

/* ---- HEAT MAP ---- */
.heat-row {{
    display: flex;
    align-items: center;
    margin-bottom: 0.25rem;
    font-size: 0.8rem;
    gap: 0.5rem;
}}

.heat-cell {{
    width: 16px;
    height: 16px;
    min-width: 16px;
    border: 1px solid rgba(134, 247, 173, 0.2);
}}

.heat-name {{
    flex: 1;
    color: #5a9e7a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.heat-errs {{
    font-size: 0.72rem;
    min-width: 80px;
    text-align: right;
}}

/* ---- FOOTER ---- */
.footer {{
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #1a3a2a;
    color: #3a6e5a;
    font-size: 0.75rem;
    text-align: center;
    letter-spacing: 1px;
}}

/* Scrollbar styling */
::-webkit-scrollbar {{
    width: 6px;
}}
::-webkit-scrollbar-track {{
    background: #010403;
}}
::-webkit-scrollbar-thumb {{
    background: #1a3a2a;
}}
::-webkit-scrollbar-thumb:hover {{
    background: #2a5a3a;
}}

/* Selection */
::selection {{
    background: rgba(134, 247, 173, 0.3);
    color: #86f7ad;
}}
</style>
</head>
<body>
<div class="dashboard">

<!-- HEADER -->
<div class="header">
    <h1>personal-index // TERMINAL DASHBOARD</h1>
    <div class="prompt">codebase projection — {data.total_modules} modules scanned</div>
</div>

<!-- 1. SURFACE STATS -->
<div class="section">
    <div class="section-title">Surface Stats</div>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{data.total_modules}</div>
            <div class="stat-label">Modules</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data.total_lines:,}</div>
            <div class="stat-label">Lines</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data.total_classes}</div>
            <div class="stat-label">Classes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data.total_functions}</div>
            <div class="stat-label">Functions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data.total_tests}</div>
            <div class="stat-label">Tests</div>
        </div>
        <div class="stat-card warn">
            <div class="stat-value">{total_warnings}</div>
            <div class="stat-label">Warnings</div>
        </div>
        <div class="stat-card err">
            <div class="stat-value">{total_errors}</div>
            <div class="stat-label">Errors</div>
        </div>
    </div>
</div>

<!-- 2. MODULE MAP -->
<div class="section">
    <div class="section-title">Module Map</div>
    <div class="module-grid">
{module_rows}
    </div>
</div>

<!-- 3. DEPENDENCY GRAPH -->
<div class="section">
    <div class="section-title">Dependency Graph</div>
    <div class="dep-tree">
{dep_tree}
    </div>
</div>

<!-- 4. TEST COVERAGE -->
<div class="section">
    <div class="section-title">Test Coverage</div>
    <div class="test-bars">
{test_bars if test_bars else '<div style="color: #5a9e7a;">No test data available.</div>'}
    </div>
</div>

<!-- 5. RECENT COMMITS -->
<div class="section">
    <div class="section-title">Recent Commits</div>
    <div class="commit-list">
{commit_rows if commit_rows else '<div style="padding: 0.5rem; color: #5a9e7a;">No commit history available.</div>'}
    </div>
</div>

<!-- 6. HEAT MAP -->
<div class="section">
    <div class="section-title">Heat Map</div>
    <div class="heat-map">
{heat_rows}
    </div>
</div>

<div class="footer">
    [ personal_index.docs_generator ] — {data.total_modules} modules | {data.total_lines:,} lines | {total_errors} errors | {total_warnings} warnings
</div>

</div>
</body>
</html>"""
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

    # Fetch recent commits
    commits = fetch_recent_commits(20)

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
        commits=commits,
    )

    print(f"[docs_generator] Generating dashboard → {output}")
    generate_dashboard(data, output)
    print(f"[docs_generator] Done. {data.total_modules} modules, {data.total_lines:,} lines, "
          f"{data.total_ruff_errors + data.total_mypy_errors} errors, "
          f"{data.total_ruff_warnings} warnings")
    return output


if __name__ == "__main__":
    generate()
