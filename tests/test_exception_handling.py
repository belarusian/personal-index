"""Tests for TICKET-48: broad exception handling fixes."""

import ast
import inspect
from pathlib import Path


def _get_source_lines(module):
    """Get source lines of a module."""
    return inspect.getsource(module)


def _find_except_blocks(source):
    """Find all except blocks in source code."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            has_logging = False
            has_error_recording = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute):
                        if isinstance(func.value, ast.Name) and func.value.id == "logger":
                            if func.attr in ("error", "warning", "exception", "critical"):
                                has_logging = True
                        if func.attr == "append":
                            has_error_recording = True

            if node.type is None:
                exc_type = "BaseException"
            elif isinstance(node.type, ast.Name):
                exc_type = node.type.id
            elif isinstance(node.type, ast.Attribute):
                exc_type = node.type.value.id + "." + node.type.attr
            elif isinstance(node.type, ast.Tuple):
                names = []
                for elt in node.type.elts:
                    if isinstance(elt, ast.Name):
                        names.append(elt.id)
                    elif isinstance(elt, ast.Attribute):
                        names.append(elt.value.id + "." + elt.attr)
                exc_type = ", ".join(names)
            else:
                exc_type = "unknown"

            results.append({
                "lineno": node.lineno,
                "exc_type": exc_type,
                "has_logging": has_logging,
                "has_error_recording": has_error_recording,
            })
    return results


class TestContentCategorizerExceptionHandling:
    """content_categorizer.py:559 - urlparse should catch ValueError, not Exception."""

    def test_urlparse_catches_value_error(self):
        from personal_index import content_categorizer
        source = _get_source_lines(content_categorizer)
        blocks = _find_except_blocks(source)
        url_hints_blocks = [b for b in blocks if 550 < b["lineno"] < 565]
        assert len(url_hints_blocks) == 1
        assert url_hints_blocks[0]["exc_type"] == "ValueError"


class TestContentLinkerExceptionHandling:
    """content_linker/linker.py:20 - urlparse should catch ValueError, not Exception."""

    def test_extract_domain_catches_value_error(self):
        from personal_index.content_linker import linker
        source = _get_source_lines(linker)
        blocks = _find_except_blocks(source)
        domain_blocks = [b for b in blocks if 15 < b["lineno"] < 25]
        assert len(domain_blocks) == 1
        assert domain_blocks[0]["exc_type"] == "ValueError"


class TestContentSchedulerExceptionHandling:
    """content_scheduler.py:180 - should log errors when catching Exception."""

    def test_run_task_logs_errors(self):
        from personal_index import content_scheduler
        source = _get_source_lines(content_scheduler)
        blocks = _find_except_blocks(source)
        task_blocks = [b for b in blocks if 175 < b["lineno"] < 195]
        exc_blocks = [b for b in task_blocks if "Exception" in b["exc_type"]]
        assert len(exc_blocks) >= 1
        assert exc_blocks[0]["has_logging"]


class TestImporterExceptionHandling:
    """importer.py:106,131,220 - should catch specific exceptions."""

    def test_json_import_catches_specific_exceptions(self):
        from personal_index import importer
        source = _get_source_lines(importer)
        blocks = _find_except_blocks(source)
        json_blocks = [b for b in blocks if 100 < b["lineno"] < 110]
        assert len(json_blocks) == 1
        assert "ValueError" in json_blocks[0]["exc_type"]

    def test_csv_import_catches_specific_exceptions(self):
        from personal_index import importer
        source = _get_source_lines(importer)
        blocks = _find_except_blocks(source)
        csv_blocks = [b for b in blocks if 125 < b["lineno"] < 135]
        assert len(csv_blocks) == 1
        assert "ValueError" in csv_blocks[0]["exc_type"]

    def test_xml_import_catches_specific_exceptions(self):
        from personal_index import importer
        source = _get_source_lines(importer)
        blocks = _find_except_blocks(source)
        xml_blocks = [b for b in blocks if 215 < b["lineno"] < 225]
        assert len(xml_blocks) == 1
        assert "ValueError" in xml_blocks[0]["exc_type"]


class TestPipelineExceptionHandling:
    """pipeline.py:99 - should log errors when catching Exception."""

    def test_pipeline_run_logs_errors(self):
        from personal_index import pipeline
        source = _get_source_lines(pipeline)
        blocks = _find_except_blocks(source)
        run_blocks = [b for b in blocks if 94 < b["lineno"] < 106]
        exc_blocks = [b for b in run_blocks if "Exception" in b["exc_type"]]
        assert len(exc_blocks) >= 1
        assert exc_blocks[0]["has_logging"]


class TestUrlHistoryExceptionHandling:
    """url_history.py:130 - urlparse should catch ValueError, not Exception."""

    def test_domain_stats_catches_value_error(self):
        from personal_index import url_history
        source = _get_source_lines(url_history)
        blocks = _find_except_blocks(source)
        domain_blocks = [b for b in blocks if 125 < b["lineno"] < 135]
        assert len(domain_blocks) == 1
        assert domain_blocks[0]["exc_type"] == "ValueError"
