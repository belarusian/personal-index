"""Adversarial deep tests for ARCH-99 (VALIDATOR, cycle 263).

ARCH-99: the `recommend` CLI command's docstring over-promised a seed-content
path ("based on a query **or seed content**") that the command never exposes.
The implementer resolved it with **Option A** (doc-only reword): the docstring
now states the exact keyword-only contract the body performs, and no seed path
is wired up.

This file pins the CORRECTED contract against the live CLI (not just the
docstring wording):

  1. The docstring no longer advertises a seed-content path.
  2. The docstring states the keyword-matching contract.
  3. The CLI input surface is keyword-only: the only argument is `query`, and
     there is NO `--seed-url` / `--seed` option.
  4. No bare `recommend(seed)` call is reachable from the CLI module source
     (only `recommend_for_keywords`).
  5. Guard inputs the contract must pin (empty index / no query / whitespace /
     no matches / negative & zero top_n) still behave per the docs.
  6. One end-to-end run through the installed CLI group.

The witness for the keyword-path behavior is the pre-existing
tests/deep/test_cli_recommend_adversarial.py (40 tests); this file is the
adversarial armor for the ARCH-99 corrected contract specifically.
"""

from __future__ import annotations

import os
import re

from click.core import Argument
from click.testing import CliRunner, Result

from personal_index.cli import main
from personal_index.cli_recommend import recommend
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


def _make_index(data_dir: str, pages: list[IndexedPage]) -> None:
    idx = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
    for p in pages:
        idx.add_page(p)


def _page(url: str, title: str = "", content: str = "", score: float = 1.0,
          keywords: list | None = None) -> IndexedPage:
    return IndexedPage(url=url, title=title, content=content, score=score,
                       keywords=keywords or [])


def _invoke(args: list[str], data_dir: str) -> "Result":
    runner = CliRunner()
    return runner.invoke(main, ["recommend", *args, "--data-dir", data_dir])


# ---------------------------------------------------------------------------
# 1 + 2: the corrected docstring contract
# ---------------------------------------------------------------------------
class TestArch99DocstringContract:
    def test_docstring_no_longer_claims_seed_path(self):
        # The over-promise ("or seed content") must be gone.
        doc = recommend.__doc__ or ""
        assert "seed content" not in doc.lower()
        assert "or seed" not in doc.lower()

    def test_docstring_states_keyword_contract(self):
        doc = (recommend.__doc__ or "").lower()
        # The corrected contract names keyword matching against indexed content.
        assert "keyword" in doc
        assert "indexed content" in doc

    def test_docstring_is_nonempty(self):
        assert (recommend.__doc__ or "").strip() != ""


# ---------------------------------------------------------------------------
# 3: the CLI input surface is keyword-only (no seed option)
# ---------------------------------------------------------------------------
class TestArch99InputSurfaceKeywordOnly:
    def test_only_argument_is_query(self):
        # The single positional argument is `query`; there is no second
        # positional (seed) argument.
        args = [p for p in recommend.params if isinstance(p, Argument)]
        assert [a.name for a in args] == ["query"]

    def test_no_seed_option_exists(self):
        # No --seed-url / --seed option is exposed.
        names = {p.name for p in recommend.params}
        assert "seed" not in names
        assert "seed_url" not in names
        # And the raw option strings do not advertise a seed flag.
        for p in recommend.params:
            for opt in p.opts:
                assert "seed" not in opt.lower()

    def test_weight_options_still_present(self):
        # The keyword-path weight options remain (they are part of the
        # reachable surface and must not have been dropped by the reword).
        names = {p.name for p in recommend.params}
        assert {"keyword_weight", "tag_weight", "score_weight"} <= names


# ---------------------------------------------------------------------------
# 4: no bare recommend(seed) call reachable from the CLI module source
# ---------------------------------------------------------------------------
class TestArch99NoSeedCallInSource:
    def test_source_has_no_bare_recommend_seed_call(self):
        import personal_index.cli_recommend as mod
        src = open(mod.__file__, encoding="utf-8").read()
        # A bare `recommend(` call (the engine's seed method) would appear as
        # `.recommend(` or `recommend(` NOT preceded by `for_keywords` and NOT
        # the `def recommend(` definition. The only `recommend(` token in the
        # module must be the command definition.
        bare_calls = re.findall(r"(?<!for_keywords)(?<!def )\brecommend\s*\(", src)
        # Filter out the `def recommend(` definition line.
        bare_calls = [
            m for m in bare_calls
            if not re.search(r"def\s+recommend\s*\(", src[max(0, m.start() - 12):m.end()])
        ]
        assert bare_calls == [], f"unexpected bare recommend( call(s): {bare_calls}"

    def test_source_calls_recommend_for_keywords(self):
        import personal_index.cli_recommend as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "recommend_for_keywords(" in src


# ---------------------------------------------------------------------------
# 5: guard inputs the contract must pin
# ---------------------------------------------------------------------------
class TestArch99GuardInputs:
    def test_empty_index_no_file(self, tmp_path):
        dd = str(tmp_path)
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "No indexed content found" in res.output

    def test_no_query_empty_keywords(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke([], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_whitespace_only_query(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["   "], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_query_no_matches(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["zzzqqq"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_top_n_negative(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--top-n", "-1"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_top_n_zero(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--top-n", "0"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output


# ---------------------------------------------------------------------------
# 6: end-to-end run through the installed CLI group
# ---------------------------------------------------------------------------
class TestArch99EndToEnd:
    def test_keyword_query_end_to_end(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python guide", "python basics", score=5.0),
            _page("https://a.com/2", "Java guide", "java basics", score=6.0),
        ])
        res = _invoke(["python", "--top-n", "1"], dd)
        assert res.exit_code == 0
        assert "Top 1 Recommendations:" in res.output
        assert "Python guide" in res.output
        assert "Java guide" not in res.output

    def test_explicit_weights_end_to_end(self, tmp_path):
        # The keyword-path weight options are still reachable and threaded
        # through (Option A did not remove them).
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python guide", "python basics", score=5.0),
        ])
        res = _invoke(
            ["python", "--keyword-weight", "1.0", "--tag-weight", "0.0",
             "--score-weight", "0.0"],
            dd,
        )
        assert res.exit_code == 0
        assert "Python guide" in res.output
