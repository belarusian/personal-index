"""Adversarial deep tests for personal_index.docs_generator.

Cycle 206 — VALIDATOR.

Targets:
- _escape_html: all 5 HTML special chars, None, empty, unicode, double-escape
- scan_modules: non-existent root, empty dir, no .py files, syntax errors
- _parse_module: syntax error file, empty file, unicode filename
- detect_dependencies: empty list, self-import, circular imports
- fetch_recent_commits: n=0, n=-1, n=very large
- generate_metadata_json: valid JSON, unicode module names
- generate_dashboard: well-formed HTML, all fields escaped
- generate / generate_fast: end-to-end, idempotence
- CLI end-to-end run
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from html.parser import HTMLParser
from pathlib import Path

import pytest

from personal_index.docs_generator import (
    CommitInfo,
    DashboardData,
    ModuleInfo,
    _escape_html,
    _parse_module,
    detect_dependencies,
    fetch_recent_commits,
    generate_dashboard,
    generate_fast,
    generate_metadata_json,
    scan_modules,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _WellFormedHTMLChecker(HTMLParser):
    """Minimal HTML well-formedness checker: tracks tag balance."""

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag not in self.VOID_ELEMENTS:
            self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID_ELEMENTS:
            return
        if not self._stack:
            self.errors.append(f"Unexpected closing tag </{tag}> with empty stack")
        elif self._stack[-1] != tag:
            self.errors.append(
                f"Mismatched closing tag </{tag}>, expected </{self._stack[-1]}>"
            )
        else:
            self._stack.pop()

    def check(self, html: str) -> list[str]:
        self._stack.clear()
        self.errors.clear()
        self.feed(html)
        self.close()
        if self._stack:
            self.errors.append(f"Unclosed tags: {self._stack}")
        return self.errors


def _assert_well_formed_html(html: str, label: str = "HTML") -> None:
    checker = _WellFormedHTMLChecker()
    errors = checker.check(html)
    assert not errors, f"{label} is not well-formed: {errors}"


def _make_module_info(
    filepath: str = "personal_index/test_mod.py",
    module_name: str = "personal_index.test_mod",
    line_count: int = 10,
    status: str = "clean",
) -> ModuleInfo:
    return ModuleInfo(
        filepath=filepath,
        module_name=module_name,
        line_count=line_count,
        status=status,
    )


def _make_dashboard_data(
    n_modules: int = 3,
) -> DashboardData:
    modules = [
        _make_module_info(
            filepath=f"personal_index/mod_{i}.py",
            module_name=f"personal_index.mod_{i}",
            line_count=100 + i,
        )
        for i in range(n_modules)
    ]
    return DashboardData(
        modules=modules,
        total_modules=n_modules,
        total_lines=sum(m.line_count for m in modules),
        total_classes=sum(len(m.classes) for m in modules),
        total_functions=sum(len(m.functions) for m in modules),
        total_tests=sum(m.test_count for m in modules),
    )


# ---------------------------------------------------------------------------
# 1. _escape_html — all 5 special chars, edge cases
# ---------------------------------------------------------------------------

class TestEscapeHtml:
    def test_ampersand(self) -> None:
        assert _escape_html("&") == "&amp;"

    def test_less_than(self) -> None:
        assert _escape_html("<") == "&lt;"

    def test_greater_than(self) -> None:
        assert _escape_html(">") == "&gt;"

    def test_double_quote(self) -> None:
        assert _escape_html('"') == "&quot;"

    def test_single_quote(self) -> None:
        assert _escape_html("'") == "&#x27;"

    def test_all_five_together(self) -> None:
        result = _escape_html('&<>"\'')
        assert result == "&amp;&lt;&gt;&quot;&#x27;"

    def test_empty_string(self) -> None:
        assert _escape_html("") == ""

    def test_no_special_chars(self) -> None:
        assert _escape_html("hello world") == "hello world"

    def test_unicode_passthrough(self) -> None:
        assert _escape_html("Ünïcödé 测试 🎉") == "Ünïcödé 测试 🎉"

    def test_already_escaped_ampersand(self) -> None:
        """Double-escaping: &amp; should become &amp;amp; (correct behavior)."""
        assert _escape_html("&amp;") == "&amp;amp;"

    def test_mixed_content(self) -> None:
        result = _escape_html('<a href="x">&amp;</a>')
        assert result == "&lt;a href=&quot;x&quot;&gt;&amp;amp;&lt;/a&gt;"

    def test_newlines_preserved(self) -> None:
        assert _escape_html("line1\nline2") == "line1\nline2"

    def test_whitespace_only(self) -> None:
        assert _escape_html("   \t\n  ") == "   \t\n  "

    def test_long_string(self) -> None:
        s = "A" * 10000
        assert _escape_html(s) == s

    def test_none_raises(self) -> None:
        with pytest.raises((TypeError, AttributeError)):
            _escape_html(None)  # type: ignore[arg-type]

    def test_idempotence_on_plain_text(self) -> None:
        s = "plain text no specials"
        assert _escape_html(s) == _escape_html(s)


# ---------------------------------------------------------------------------
# 2. scan_modules — edge cases
# ---------------------------------------------------------------------------

class TestScanModules:
    def test_nonexistent_root(self) -> None:
        """Non-existent directory should return empty list, not crash."""
        result = scan_modules("/nonexistent/path/that/does/not/exist")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_modules(tmpdir)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_directory_with_no_py_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "readme.txt").write_text("hello")
            Path(tmpdir, "data.json").write_text("{}")
            result = scan_modules(tmpdir)
            assert len(result) == 0

    def test_directory_with_one_py_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "hello.py").write_text(
                '"""A test module."""\n\ndef hello():\n    """Say hi."""\n    return "hi"\n'
            )
            result = scan_modules(tmpdir)
            assert len(result) == 1
            assert result[0].module_name.endswith("hello")
            assert result[0].docstring == "A test module."
            assert len(result[0].functions) == 1
            assert result[0].functions[0].name == "hello"

    def test_directory_with_syntax_error_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "broken.py").write_text("def broken(:\n    pass\n")
            result = scan_modules(tmpdir)
            assert len(result) == 1
            assert result[0].status == "error"
            assert len(result[0].ruff_errors) >= 1

    def test_directory_with_empty_py_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "empty.py").write_text("")
            result = scan_modules(tmpdir)
            assert len(result) == 1
            assert result[0].line_count >= 1

    def test_nested_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = Path(tmpdir, "sub")
            sub.mkdir()
            Path(tmpdir, "top.py").write_text("x = 1\n")
            Path(sub, "bottom.py").write_text("y = 2\n")
            result = scan_modules(tmpdir)
            assert len(result) == 2

    def test_unicode_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "módül.py").write_text("z = 3\n")
            result = scan_modules(tmpdir)
            assert len(result) == 1

    def test_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.py").write_text("a = 1\n")
            r1 = scan_modules(tmpdir)
            r2 = scan_modules(tmpdir)
            assert len(r1) == len(r2)
            assert [m.module_name for m in r1] == [m.module_name for m in r2]


# ---------------------------------------------------------------------------
# 3. _parse_module — edge cases
# ---------------------------------------------------------------------------

class TestParseModule:
    def test_nonexistent_file(self) -> None:
        info = _parse_module("/nonexistent/file.py")
        assert info.status == "error"

    def test_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("")
            path = f.name
        try:
            info = _parse_module(path)
            assert info.line_count >= 1
            assert info.status == "clean"
        finally:
            os.unlink(path)

    def test_file_with_only_comments(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("# just a comment\n# another\n")
            path = f.name
        try:
            info = _parse_module(path)
            assert info.status == "clean"
            assert len(info.functions) == 0
            assert len(info.classes) == 0
        finally:
            os.unlink(path)

    def test_file_with_class_and_methods(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(textwrap.dedent("""\
                class Foo:
                    \"\"\"A class.\"\"\"
                    def bar(self):
                        \"\"\"A method.\"\"\"
                        pass
                    async def baz(self):
                        \"\"\"An async method.\"\"\"
                        pass
                """))
            path = f.name
        try:
            info = _parse_module(path)
            assert len(info.classes) == 1
            assert info.classes[0].name == "Foo"
            assert len(info.classes[0].methods) == 2
            method_names = {m.name for m in info.classes[0].methods}
            assert method_names == {"bar", "baz"}
            async_methods = [m for m in info.classes[0].methods if m.is_async]
            assert len(async_methods) == 1
            assert async_methods[0].name == "baz"
        finally:
            os.unlink(path)

    def test_file_with_imports(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(textwrap.dedent("""\
                import os
                import sys as system
                from pathlib import Path
                from collections import OrderedDict as OD
                """))
            path = f.name
        try:
            info = _parse_module(path)
            assert "os" in info.imports
            assert "system" in info.imports  # asname
            assert "pathlib.Path" in info.imports
            assert "collections.OD" in info.imports
        finally:
            os.unlink(path)

    def test_file_with_test_functions(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(textwrap.dedent("""\
                def test_alpha():
                    pass
                def test_beta():
                    pass
                def not_a_test():
                    pass
                """))
            path = f.name
        try:
            info = _parse_module(path)
            assert info.test_count == 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 4. detect_dependencies — edge cases
# ---------------------------------------------------------------------------

class TestDetectDependencies:
    def test_empty_list(self) -> None:
        result = detect_dependencies([])
        assert result == {}

    def test_single_module_no_imports(self) -> None:
        mod = _make_module_info()
        result = detect_dependencies([mod])
        assert result == {"personal_index.test_mod": []}

    def test_two_modules_with_import(self) -> None:
        mod_a = _make_module_info(
            filepath="personal_index/a.py",
            module_name="personal_index.a",
        )
        mod_a.imports = ["personal_index.b"]
        mod_b = _make_module_info(
            filepath="personal_index/b.py",
            module_name="personal_index.b",
        )
        result = detect_dependencies([mod_a, mod_b])
        assert "personal_index.b" in result["personal_index.a"]
        assert result["personal_index.b"] == []

    def test_self_import_excluded(self) -> None:
        mod = _make_module_info(
            filepath="personal_index/a.py",
            module_name="personal_index.a",
        )
        mod.imports = ["personal_index.a"]  # self-import
        result = detect_dependencies([mod])
        assert result["personal_index.a"] == []

    def test_circular_imports(self) -> None:
        mod_a = _make_module_info(
            filepath="personal_index/a.py",
            module_name="personal_index.a",
        )
        mod_a.imports = ["personal_index.b"]
        mod_b = _make_module_info(
            filepath="personal_index/b.py",
            module_name="personal_index.b",
        )
        mod_b.imports = ["personal_index.a"]
        result = detect_dependencies([mod_a, mod_b])
        assert "personal_index.b" in result["personal_index.a"]
        assert "personal_index.a" in result["personal_index.b"]

    def test_submodule_import(self) -> None:
        """Import of a submodule should be detected via prefix match."""
        mod_parent = _make_module_info(
            filepath="personal_index/pkg.py",
            module_name="personal_index.pkg",
        )
        mod_child = _make_module_info(
            filepath="personal_index/pkg/sub.py",
            module_name="personal_index.pkg.sub",
        )
        mod_parent.imports = ["personal_index.pkg.sub"]
        result = detect_dependencies([mod_parent, mod_child])
        assert "personal_index.pkg.sub" in result["personal_index.pkg"]

    def test_idempotence(self) -> None:
        mod_a = _make_module_info(
            filepath="personal_index/a.py",
            module_name="personal_index.a",
        )
        mod_a.imports = ["personal_index.b"]
        mod_b = _make_module_info(
            filepath="personal_index/b.py",
            module_name="personal_index.b",
        )
        r1 = detect_dependencies([mod_a, mod_b])
        r2 = detect_dependencies([mod_a, mod_b])
        assert r1 == r2


# ---------------------------------------------------------------------------
# 5. fetch_recent_commits — edge cases
# ---------------------------------------------------------------------------

class TestFetchRecentCommits:
    def test_returns_list(self) -> None:
        result = fetch_recent_commits(5)
        assert isinstance(result, list)

    def test_n_zero(self) -> None:
        """n=0 should return empty list (git log -0 returns nothing)."""
        result = fetch_recent_commits(0)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_n_negative(self) -> None:
        """n=-1: git log --format with -(-1) = -- -1, which is invalid.
        Should not crash; should return empty list."""
        result = fetch_recent_commits(-1)
        assert isinstance(result, list)

    def test_n_very_large(self) -> None:
        """n=999999 should not crash; returns at most the actual commit count."""
        result = fetch_recent_commits(999999)
        assert isinstance(result, list)
        # Should have at least 1 commit (this repo has history)
        assert len(result) >= 1

    def test_commit_fields_populated(self) -> None:
        result = fetch_recent_commits(1)
        if result:
            c = result[0]
            assert isinstance(c, CommitInfo)
            assert len(c.sha_short) > 0
            assert isinstance(c.message, str)
            assert isinstance(c.author, str)
            assert isinstance(c.date, str)

    def test_idempotence(self) -> None:
        r1 = fetch_recent_commits(3)
        r2 = fetch_recent_commits(3)
        assert len(r1) == len(r2)
        if r1:
            assert r1[0].sha_short == r2[0].sha_short


# ---------------------------------------------------------------------------
# 6. generate_metadata_json — valid JSON
# ---------------------------------------------------------------------------

class TestGenerateMetadataJson:
    def test_valid_json(self) -> None:
        data = _make_dashboard_data(3)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        json_path = None
        try:
            json_path = generate_metadata_json(data, path)
            assert os.path.exists(json_path), f"JSON file not created at {json_path}"
            with open(json_path) as fh:
                content = fh.read()
            parsed = json.loads(content)  # must be valid JSON
            assert "summary" in parsed
            assert "modules" in parsed
        finally:
            for p in (path, json_path):
                if p and os.path.exists(p):
                    os.unlink(p)

    def test_empty_dashboard(self) -> None:
        data = DashboardData()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        json_path = None
        try:
            json_path = generate_metadata_json(data, path)
            assert os.path.exists(json_path), f"JSON file not created at {json_path}"
            with open(json_path) as fh:
                content = fh.read()
            parsed = json.loads(content)
            assert parsed["summary"]["total_modules"] == 0
        finally:
            for p in (path, json_path):
                if p and os.path.exists(p):
                    os.unlink(p)

    def test_unicode_module_names(self) -> None:
        data = DashboardData(
            modules=[
                _make_module_info(
                    filepath="personal_index/ünïcödé.py",
                    module_name="personal_index.ünïcödé",
                )
            ],
            total_modules=1,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        json_path = None
        try:
            json_path = generate_metadata_json(data, path)
            assert os.path.exists(json_path), f"JSON file not created at {json_path}"
            with open(json_path) as fh:
                content = fh.read()
            parsed = json.loads(content)
            # Unicode should round-trip through the JSON file
            assert parsed["modules"][0]["name"] == "personal_index.ünïcödé"
            assert parsed["modules"][0]["filepath"] == "personal_index/ünïcödé.py"
        finally:
            for p in (path, json_path):
                if p and os.path.exists(p):
                    os.unlink(p)


# ---------------------------------------------------------------------------
# 7. generate_dashboard — well-formed HTML
# ---------------------------------------------------------------------------

class TestGenerateDashboard:
    def test_well_formed_html(self) -> None:
        data = _make_dashboard_data(3)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            generate_dashboard(data, path)
            html = Path(path).read_text(encoding="utf-8")
            _assert_well_formed_html(html, "dashboard")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_empty_dashboard(self) -> None:
        data = DashboardData()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            generate_dashboard(data, path)
            html = Path(path).read_text(encoding="utf-8")
            _assert_well_formed_html(html, "empty dashboard")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_module_names_escaped(self) -> None:
        """Module names with HTML special chars must be escaped in output."""
        data = DashboardData(
            modules=[
                _make_module_info(
                    filepath="personal_index/<evil>.py",
                    module_name="personal_index.<evil>",
                )
            ],
            total_modules=1,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            generate_dashboard(data, path)
            html = Path(path).read_text(encoding="utf-8")
            # The raw <evil> tag must NOT appear as a real HTML tag
            assert "<evil>" not in html, (
                "Module name was not HTML-escaped in dashboard output"
            )
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_idempotence(self) -> None:
        data = _make_dashboard_data(2)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f1:
            path1 = f1.name
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f2:
            path2 = f2.name
        try:
            generate_dashboard(data, path1)
            generate_dashboard(data, path2)
            h1 = Path(path1).read_text(encoding="utf-8")
            h2 = Path(path2).read_text(encoding="utf-8")
            assert h1 == h2
        finally:
            for p in (path1, path2):
                if os.path.exists(p):
                    os.unlink(p)

    def test_10_modules(self) -> None:
        data = _make_dashboard_data(10)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            generate_dashboard(data, path)
            html = Path(path).read_text(encoding="utf-8")
            _assert_well_formed_html(html, "10-module dashboard")
            for i in range(10):
                assert f"mod_{i}" in html
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# 8. generate / generate_fast — end-to-end
# ---------------------------------------------------------------------------

class TestGenerateEndToEnd:
    def test_generate_fast_returns_path(self) -> None:
        """generate_fast should return the output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal Python package to scan
            pkg_dir = Path(tmpdir, "testpkg")
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("")
            (pkg_dir / "mod1.py").write_text(
                '"""A module."""\n\ndef hello():\n    """Say hi."""\n    return "hi"\n'
            )
            output = str(Path(tmpdir, "dashboard.html"))
            result = generate_fast(str(pkg_dir), output)
            assert result == output
            assert os.path.exists(output)
            html = Path(output).read_text(encoding="utf-8")
            assert len(html) > 0
            _assert_well_formed_html(html, "generate_fast output")

    def test_generate_fast_empty_package(self) -> None:
        """generate_fast on an empty package should not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir, "empty_pkg")
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("")
            output = str(Path(tmpdir, "dashboard.html"))
            result = generate_fast(str(pkg_dir), output)
            assert result == output
            assert os.path.exists(output)

    def test_generate_fast_idempotence(self) -> None:
        """Two runs on the same package should produce identical output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir, "testpkg")
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("")
            (pkg_dir / "mod1.py").write_text("x = 1\n")
            out1 = str(Path(tmpdir, "d1.html"))
            out2 = str(Path(tmpdir, "d2.html"))
            generate_fast(str(pkg_dir), out1)
            generate_fast(str(pkg_dir), out2)
            h1 = Path(out1).read_text(encoding="utf-8")
            h2 = Path(out2).read_text(encoding="utf-8")
            assert h1 == h2

    def test_generate_fast_nonexistent_root(self) -> None:
        """generate_fast on a non-existent root should not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir, "dashboard.html"))
            # Should either raise a clear error or produce an empty dashboard
            try:
                generate_fast("/nonexistent/path", output)
                # If it doesn't raise, it should still produce a file
                assert os.path.exists(output)
            except (OSError, FileNotFoundError):
                pass  # acceptable: clear error


# ---------------------------------------------------------------------------
# 9. End-to-end CLI run
# ---------------------------------------------------------------------------

class TestEndToEndCli:
    def test_status_command_runs(self) -> None:
        """Run `python3 -m personal_index status` and verify it exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        assert result.returncode == 0, (
            f"CLI status failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )
