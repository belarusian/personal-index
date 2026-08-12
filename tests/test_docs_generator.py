"""Tests for personal_index.docs_generator."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from unittest import mock

from personal_index.docs_generator import (
    DashboardData,
    ModuleInfo,
    _ast_name,
    _escape_html,
    _extract_docstring,
    _filepath_to_module,
    _parse_module,
    _status_bg,
    _status_color,
    detect_dependencies,
    generate,
    generate_dashboard,
    run_mypy,
    run_pytest,
    run_ruff,
    scan_modules,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_tmp_module(tmp_path: Path, name: str, source: str) -> Path:
    """Write a Python file into a temp directory and return its path."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Unit tests: AST helpers
# ---------------------------------------------------------------------------

class TestExtractDocstring:
    def test_returns_docstring(self):
        source = 'def f():\n    """hello"""\n    pass'
        tree = ast.parse(source)
        node = tree.body[0]
        assert _extract_docstring(node) == "hello"

    def test_returns_empty_for_no_docstring(self):
        source = "def f(): pass"
        tree = ast.parse(source)
        node = tree.body[0]
        assert _extract_docstring(node) == ""


class TestFilepathToModule:
    def test_simple(self):
        assert _filepath_to_module("personal_index/cli.py") == "personal_index.cli"

    def test_nested(self):
        assert _filepath_to_module("personal_index/api/handlers.py") == "personal_index.api.handlers"

    def test_init(self):
        assert _filepath_to_module("personal_index/__init__.py") == "personal_index.__init__"


class TestAstName:
    def test_name_node(self):
        node = ast.Name(id="foo")
        assert _ast_name(node) == "foo"

    def test_attribute_node(self):
        node = ast.Attribute(value=ast.Name(id="os"), attr="path")
        assert _ast_name(node) == "os.path"


# ---------------------------------------------------------------------------
# Unit tests: _parse_module
# ---------------------------------------------------------------------------

class TestParseModule:
    def test_parses_functions_and_classes(self, tmp_path: Path):
        src = """
class MyClass:
    '''A class.'''
    def method_a(self):
        pass

def standalone():
    '''A function.'''
    pass
"""
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert len(info.classes) == 1
        assert info.classes[0].name == "MyClass"
        assert info.classes[0].docstring == "A class."
        assert len(info.classes[0].methods) == 1
        assert info.classes[0].methods[0].name == "method_a"
        assert len(info.functions) == 1
        assert info.functions[0].name == "standalone"

    def test_counts_lines(self, tmp_path: Path):
        src = "\n".join([f"# line {i}" for i in range(1, 52)])
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert info.line_count == 50

    def test_captures_imports(self, tmp_path: Path):
        src = """
import os
import json as j
from pathlib import Path
"""
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert "os" in info.imports
        assert "j" in info.imports
        assert "pathlib.Path" in info.imports

    def test_syntax_error_sets_status(self, tmp_path: Path):
        src = "def broken("
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert info.status == "error"
        assert any("SyntaxError" in e for e in info.ruff_errors)

    def test_module_docstring(self, tmp_path: Path):
        src = '''"""Module doc."""\n\ndef f(): pass\n'''
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert info.docstring == "Module doc."

    def test_async_function(self, tmp_path: Path):
        src = "async def af(): pass"
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert len(info.functions) == 1
        assert info.functions[0].is_async is True

    def test_class_bases(self, tmp_path: Path):
        src = "class Foo(BaseMixin, Other): pass"
        p = _write_tmp_module(tmp_path, "mod.py", src)
        info = _parse_module(str(p))
        assert info.classes[0].bases == ["BaseMixin", "Other"]


# ---------------------------------------------------------------------------
# Unit tests: scan_modules
# ---------------------------------------------------------------------------

class TestScanModules:
    def test_finds_modules_in_personal_index(self):
        modules = scan_modules("personal_index")
        assert len(modules) > 0
        names = {m.module_name for m in modules}
        assert "personal_index.__init__" in names
        assert "personal_index.cli" in names

    def test_returns_module_info_objects(self):
        modules = scan_modules("personal_index")
        for m in modules:
            assert isinstance(m, ModuleInfo)
            assert m.module_name.startswith("personal_index")
            assert m.line_count > 0


# ---------------------------------------------------------------------------
# Unit tests: detect_dependencies
# ---------------------------------------------------------------------------

class TestDetectDependencies:
    def test_basic_dependency(self):
        mod_a = ModuleInfo(filepath="a.py", module_name="a", imports=["b"])
        mod_b = ModuleInfo(filepath="b.py", module_name="b", imports=[])
        graph = detect_dependencies([mod_a, mod_b])
        assert "b" in graph["a"]

    def test_no_self_dependency(self):
        mod_a = ModuleInfo(filepath="a.py", module_name="a", imports=["a"])
        graph = detect_dependencies([mod_a])
        assert "a" not in graph.get("a", [])

    def test_empty_graph(self):
        mod_a = ModuleInfo(filepath="a.py", module_name="a", imports=[])
        graph = detect_dependencies([mod_a])
        assert graph["a"] == []


# ---------------------------------------------------------------------------
# Unit tests: tool runners (mocked)
# ---------------------------------------------------------------------------

class TestRunRuff:
    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_populates_ruff_errors(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="personal_index/cli.py:10: F401 unused import\n",
            stderr="",
        )
        modules = [ModuleInfo(filepath="personal_index/cli.py", module_name="personal_index.cli")]
        run_ruff(modules)
        assert len(modules[0].ruff_errors) > 0

    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_sets_status_error(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="personal_index/cli.py:10: F401 unused import\n",
            stderr="",
        )
        modules = [ModuleInfo(filepath="personal_index/cli.py", module_name="personal_index.cli")]
        run_ruff(modules)
        assert modules[0].status == "error"

    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_handles_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="ruff", timeout=120)
        modules = [ModuleInfo(filepath="a.py", module_name="a")]
        run_ruff(modules)  # should not raise


class TestRunMypy:
    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_populates_mypy_errors(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="personal_index/cli.py:10: error: reveal type\n",
            stderr="",
        )
        modules = [ModuleInfo(filepath="personal_index/cli.py", module_name="personal_index.cli")]
        run_mypy(modules)
        assert len(modules[0].mypy_errors) > 0

    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_handles_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="mypy", timeout=120)
        modules = [ModuleInfo(filepath="a.py", module_name="a")]
        run_mypy(modules)  # should not raise


class TestRunPytest:
    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_returns_summary(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            stdout="500 passed in 2.00s",
            stderr="",
        )
        modules = [ModuleInfo(filepath="a.py", module_name="a")]
        result = run_pytest(modules)
        assert "500 passed" in result

    @mock.patch("personal_index.docs_generator.subprocess.run")
    def test_handles_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="pytest", timeout=120)
        modules = [ModuleInfo(filepath="a.py", module_name="a")]
        result = run_pytest(modules)
        assert "could not be run" in result


# ---------------------------------------------------------------------------
# Unit tests: HTML helpers
# ---------------------------------------------------------------------------

class TestEscapeHtml:
    def test_escapes_special_chars(self):
        assert _escape_html('<div class="test">&</div>') == "&lt;div class=&quot;test&quot;&gt;&amp;&lt;/div&gt;"

    def test_plain_text_unchanged(self):
        assert _escape_html("hello world") == "hello world"


class TestStatusColor:
    def test_clean(self):
        assert _status_color("clean") == "#22c55e"

    def test_warning(self):
        assert _status_color("warning") == "#eab308"

    def test_error(self):
        assert _status_color("error") == "#ef4444"

    def test_unknown(self):
        assert _status_color("unknown") == "#6b7280"


class TestStatusBg:
    def test_clean(self):
        assert _status_bg("clean") == "#166534"

    def test_warning(self):
        assert _status_bg("warning") == "#854d0e"

    def test_error(self):
        assert _status_bg("error") == "#991b1b"


# ---------------------------------------------------------------------------
# Unit tests: generate_dashboard
# ---------------------------------------------------------------------------

class TestGenerateDashboard:
    def test_creates_html_file(self, tmp_path: Path):
        out = tmp_path / "dashboard.html"
        data = DashboardData(
            modules=[
                ModuleInfo(filepath="a.py", module_name="a", line_count=10, status="clean"),
                ModuleInfo(filepath="b.py", module_name="b", line_count=20, status="error"),
            ],
            total_modules=2,
            total_lines=30,
            total_classes=0,
            total_functions=0,
            total_tests=0,
            total_ruff_errors=1,
            total_ruff_warnings=0,
            total_mypy_errors=0,
            dependency_graph={"a": ["b"]},
            test_results="2 passed",
        )
        generate_dashboard(data, str(out))
        content = out.read_text()
        assert "<!DOCTYPE html>" in content
        assert "personal-index" in content
        assert "a" in content
        assert "b" in content
        assert "TERMINAL DASHBOARD" in content
        assert "1 errors" in content
        # Dark theme check
        assert "#010403" in content
        # No external dependencies
        assert "http:" not in content
        assert "https:" not in content

    def test_escapes_module_names(self, tmp_path: Path):
        out = tmp_path / "dashboard.html"
        data = DashboardData(
            modules=[
                ModuleInfo(filepath="x.py", module_name="x<y>", line_count=1, status="clean"),
            ],
            total_modules=1,
            total_lines=1,
        )
        generate_dashboard(data, str(out))
        content = out.read_text()
        assert "<y>" not in content
        assert "&lt;y&gt;" in content

    def test_empty_modules(self, tmp_path: Path):
        out = tmp_path / "dashboard.html"
        data = DashboardData()
        generate_dashboard(data, str(out))
        content = out.read_text()
        assert "<!DOCTYPE html>" in content
        assert "No test data available" in content


# ---------------------------------------------------------------------------
# Integration test: generate()
# ---------------------------------------------------------------------------

class TestGenerate:
    @mock.patch("personal_index.docs_generator.scan_modules")
    @mock.patch("personal_index.docs_generator.run_ruff")
    @mock.patch("personal_index.docs_generator.run_mypy")
    @mock.patch("personal_index.docs_generator.run_pytest")
    @mock.patch("personal_index.docs_generator.generate_dashboard")
    def test_full_pipeline(
        self,
        mock_dashboard,
        mock_pytest,
        mock_mypy,
        mock_ruff,
        mock_scan,
        tmp_path: Path,
    ):
        mock_scan.side_effect = lambda path: [
            ModuleInfo(filepath="a.py", module_name="a", line_count=10),
        ] if path == "fake" else []
        mock_pytest.return_value = "1 passed"
        out = tmp_path / "out.html"
        result = generate(root="fake", output=str(out))
        assert result == str(out)
        assert mock_scan.call_count == 2
        mock_scan.assert_any_call("fake")
        mock_ruff.assert_called_once()
        mock_mypy.assert_called_once()
        mock_pytest.assert_called_once()
        mock_dashboard.assert_called_once()
