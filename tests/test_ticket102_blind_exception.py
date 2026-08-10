"""Tests for TICKET-102: Fix blind exception handling in crawler modules."""

from __future__ import annotations

import ast
import os

import pytest


def _read_file(path: str) -> str:
    """Read file content."""
    base = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(base, path), "r") as f:
        return f.read()


def _find_except_handlers(path: str) -> list[str]:
    """Find all bare 'except Exception:' handlers in a file."""
    content = _read_file(path)
    tree = ast.parse(content)
    handlers: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is not None:
                type_name = ast.unparse(node.type)
                handlers.append(type_name)
            else:
                handlers.append("bare")
    return handlers


class TestCrawlerExceptionHandling:
    """Verify crawler modules don't use blind exception handling."""

    def test_crawler_init_no_bare_exception(self):
        """crawler/__init__.py should not catch bare Exception."""
        handlers = _find_except_handlers("personal_index/crawler/__init__.py")
        # Should have specific exception types, not bare Exception
        assert "Exception" not in handlers, (
            "crawler/__init__.py catches bare Exception which hides "
            "KeyboardInterrupt, SystemExit, etc."
        )

    def test_crawler_main_no_bare_exception(self):
        """crawler/main.py should not catch bare Exception."""
        handlers = _find_except_handlers("personal_index/crawler/main.py")
        assert "Exception" not in handlers, (
            "crawler/main.py catches bare Exception which hides "
            "KeyboardInterrupt, SystemExit, etc."
        )

    def test_crawler_init_uses_requests_exception(self):
        """crawler/__init__.py should catch requests.RequestException."""
        handlers = _find_except_handlers("personal_index/crawler/__init__.py")
        assert "requests.RequestException" in handlers, (
            "crawler/__init__.py should catch requests.RequestException"
        )

    def test_crawler_main_uses_requests_exception(self):
        """crawler/main.py should catch requests.RequestException."""
        handlers = _find_except_handlers("personal_index/crawler/main.py")
        assert "requests.RequestException" in handlers, (
            "crawler/main.py should catch requests.RequestException"
        )

    def test_crawler_init_keyboard_interrupt_not_caught(self):
        """Verify KeyboardInterrupt is not swallowed in crawler/__init__.py."""
        content = _read_file("personal_index/crawler/__init__.py")
        # The _fetch method should not catch Exception (which would include KeyboardInterrupt)
        assert "except Exception:" not in content, (
            "crawler/__init__.py still has 'except Exception:' which "
            "would swallow KeyboardInterrupt"
        )

    def test_crawler_main_keyboard_interrupt_not_caught(self):
        """Verify KeyboardInterrupt is not swallowed in crawler/main.py."""
        content = _read_file("personal_index/crawler/main.py")
        assert "except Exception:" not in content, (
            "crawler/main.py still has 'except Exception:' which "
            "would swallow KeyboardInterrupt"
        )
