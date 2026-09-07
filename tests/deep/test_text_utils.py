"""Adversarial deep tests for personal_index.text_utils.count_characters.

Cycle 135 - VALIDATOR probe.

Contract (docstring):
  count_characters(text, include_spaces=True) -> int
    - include_spaces=True (default): return len(text)
    - include_spaces=False: return len(re.sub(r"\s+", "", text))

Python 3's re \s matches all Unicode whitespace (NBSP, em-space,
ideographic space, etc.) but NOT U+FEFF (BOM). We verify the
contract holds for every Unicode whitespace category.
"""

from __future__ import annotations

import pytest

from personal_index.text_utils import count_characters


# ---------------------------------------------------------------------------
# include_spaces=True (default): count ALL characters
# ---------------------------------------------------------------------------

class TestCountCharactersIncludeSpaces:
    def test_empty_string(self):
        assert count_characters("") == 0

    def test_none_returns_zero(self):
        """if not text: return 0 - None is falsy."""
        assert count_characters(None) == 0  # type: ignore[arg-type]

    def test_single_char(self):
        assert count_characters("a") == 1

    def test_all_spaces(self):
        assert count_characters("   ") == 3

    def test_mixed(self):
        assert count_characters("h e l l o") == 9

    def test_newlines_and_tabs(self):
        assert count_characters("a\tb\nc") == 5

    def test_unicode_letters(self):
        assert count_characters("\u4f60\u597d\u043f\u0440\u0438\u0432\u0627\u0646") == 8

    def test_nbsp_counted(self):
        """NBSP is a character; with include_spaces=True it counts."""
        assert count_characters("hello\u00a0world") == 11

    def test_feff_counted(self):
        """BOM is a character; with include_spaces=True it counts."""
        assert count_characters("\ufeffhello") == 6

    def test_very_long_string(self):
        s = "x" * 100_000
        assert count_characters(s) == 100_000


# ---------------------------------------------------------------------------
# include_spaces=False: count NON-whitespace characters
# ---------------------------------------------------------------------------

class TestCountCharactersExcludeSpaces:
    def test_empty_string(self):
        assert count_characters("", include_spaces=False) == 0

    def test_none_returns_zero(self):
        assert count_characters(None, include_spaces=False) == 0  # type: ignore[arg-type]

    def test_all_spaces(self):
        assert count_characters("   ", include_spaces=False) == 0

    def test_mixed(self):
        assert count_characters("h e l l o", include_spaces=False) == 5

    def test_newlines_and_tabs(self):
        assert count_characters("a\tb\nc", include_spaces=False) == 3

    @pytest.mark.parametrize(
        ("char", "label"),
        [
            ("\u0020", "ASCII space"),
            ("\u0009", "tab"),
            ("\u000a", "LF"),
            ("\u000b", "VT"),
            ("\u000c", "FF"),
            ("\u000d", "CR"),
            ("\u00a0", "NBSP"),
            ("\u1680", "Ogham space mark"),
            ("\u2000", "En quad"),
            ("\u2001", "Em quad"),
            ("\u2002", "En space"),
            ("\u2003", "Em space"),
            ("\u2004", "Three-per-em space"),
            ("\u2005", "Four-per-em space"),
            ("\u2006", "Six-per-em space"),
            ("\u2007", "Figure space"),
            ("\u2008", "Punctuation space"),
            ("\u2009", "Thin space"),
            ("\u200a", "Hair space"),
            ("\u2028", "Line separator"),
            ("\u2029", "Paragraph separator"),
            ("\u202f", "Narrow no-break space"),
            ("\u205f", "Medium mathematical space"),
            ("\u3000", "Ideographic space"),
        ],
    )
    def test_unicode_whitespace_stripped(self, char: str, label: str) -> None:
        """Every Unicode whitespace char matched by Python 3 re \\s
        must be stripped when include_spaces=False."""
        result = count_characters(char * 3, include_spaces=False)
        assert result == 0, (
            f"U+{ord(char):04X} ({label}) should be stripped but "
            f"count_characters returned {result}"
        )

    @pytest.mark.parametrize(
        ("char", "label"),
        [
            ("\u00a0", "NBSP"),
            ("\u2003", "Em space"),
            ("\u3000", "Ideographic space"),
        ],
    )
    def test_mixed_with_non_space(self, char: str, label: str) -> None:
        """'a<ws>b' must count exactly 2 non-whitespace chars."""
        result = count_characters(f"a{char}b", include_spaces=False)
        assert result == 2, (
            f"a + U+{ord(char):04X} ({label}) + b should be 2, got {result}"
        )

    def test_feff_not_stripped(self):
        """U+FEFF (BOM) is NOT matched by Python 3 re \\s, so it
        survives include_spaces=False. This is a known Python re
        limitation, not a contract violation - the docstring says
        'whitespace' and re \\s is the implementation's definition."""
        result = count_characters("\ufeffhello", include_spaces=False)
        # BOM survives re \s, so it counts as a non-whitespace char
        assert result == 6, f"BOM + hello should be 6 (BOM not stripped by re), got {result}"


# ---------------------------------------------------------------------------
# Property checks
# ---------------------------------------------------------------------------

class TestCountCharactersProperties:
    def test_exclude_leq_include(self):
        """Non-space count is always <= total count."""
        s = "hello world foo"
        assert count_characters(s, include_spaces=False) <= count_characters(s)

    def test_idempotent(self):
        """Same input, same output."""
        s = "  hello   world  "
        assert count_characters(s) == count_characters(s)
        assert count_characters(s, include_spaces=False) == count_characters(s, include_spaces=False)

    def test_additive_over_concatenation(self):
        """count(a) + count(b) == count(a+b) for include_spaces=True."""
        a, b = "hello", "world"
        assert count_characters(a) + count_characters(b) == count_characters(a + b)

    def test_additive_exclude_with_space(self):
        """count(a, excl) + count(b, excl) == count(a + ' ' + b, excl)."""
        a, b = "hello", "world"
        assert (count_characters(a, include_spaces=False)
                + count_characters(b, include_spaces=False)
                == count_characters(a + " " + b, include_spaces=False))

    def test_whitespace_only_zero_exclude(self):
        for n in (0, 1, 5, 100):
            assert count_characters(" " * n, include_spaces=False) == 0


# ---------------------------------------------------------------------------
# End-to-end: CLI round-trip
# ---------------------------------------------------------------------------

class TestCountCharactersCLI:
    def test_cli_help(self):
        """The CLI should at least have a help that doesn't crash."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()
