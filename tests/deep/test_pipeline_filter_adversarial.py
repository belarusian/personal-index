"""Adversarial deep tests for ARCH-97 (cli_verify dead _run_filter removal).

ARCH-97 contract (tickets/ARCH-97.md, IMPLEMENTED #1564@dcf0461):

- Option A was taken: the dead helper ``_run_filter`` (a ``tuple[bool, str]``
  duplicate of the ``bool``-returning ``_verify_filter``) is DELETED from
  ``personal_index/cli_verify.py``. Nothing in the module should reference it.
- The full-pipeline self-test ``_check_full_pipeline`` still reports a
  non-empty, filter-mentioning reason when the filter stage rejects a page,
  and ``(True, "")`` when it passes.

These tests pin the *production* filter path (not the deleted helper) and
attack it with adversarial inputs: forced rejection, forced acceptance, and
the dead-symbol absence. They never modify source.
"""

from __future__ import annotations

from personal_index import cli_verify
from personal_index.content_filter import ContentFilter


class TestDeadHelperRemoved:
    """Acceptance criterion 1: _run_filter is gone from the module."""

    def test_run_filter_attribute_absent(self):
        """The dead helper must not exist as a module attribute."""
        assert not hasattr(cli_verify, "_run_filter"), (
            "ARCH-97: _run_filter should have been deleted (Option A); "
            "it is still present on personal_index.cli_verify"
        )

    def test_run_filter_not_in_module_source(self):
        """No 'def _run_filter' or call site may remain in the module source."""
        import inspect

        src = inspect.getsource(cli_verify)
        assert "def _run_filter" not in src, (
            "ARCH-97: 'def _run_filter' still present in cli_verify source"
        )
        # The surviving filter check the pipeline calls must still be there.
        assert "def _verify_filter" in src

    def test_verify_filter_still_callable(self):
        """The surviving helper must remain importable and callable."""
        assert callable(cli_verify._verify_filter)


class TestFullPipelineFilterRejection:
    """Acceptance criteria 2-3: rejection yields (False, <non-empty reason>)."""

    def test_rejection_returns_false_and_nonempty_reason(self, tmp_path, monkeypatch):
        """Forcing should_include -> False must yield (False, non-empty)."""
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: False
        )
        passed, error = cli_verify._check_full_pipeline(str(tmp_path))
        assert passed is False
        assert isinstance(error, str)
        assert error != "", "rejection reason must be non-empty"

    def test_rejection_reason_mentions_filter(self, tmp_path, monkeypatch):
        """The rejection reason must name the filter stage."""
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: False
        )
        passed, error = cli_verify._check_full_pipeline(str(tmp_path))
        assert passed is False
        assert "filter" in error.lower(), (
            f"rejection reason should mention the filter stage, got: {error!r}"
        )

    def test_rejection_reason_is_stable_string(self, tmp_path, monkeypatch):
        """The reason is the hard-coded 'Filter rejected valid content'."""
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: False
        )
        _, error = cli_verify._check_full_pipeline(str(tmp_path))
        assert "Filter rejected valid content" in error


class TestFullPipelineFilterAcceptance:
    """Acceptance criterion 2: a passing filter still yields (True, '')."""

    def test_acceptance_returns_true_empty(self, tmp_path):
        """Unpatched (real) filter on the generated page must pass."""
        passed, error = cli_verify._check_full_pipeline(str(tmp_path))
        assert passed is True
        assert error == ""

    def test_acceptance_idempotent(self, tmp_path, monkeypatch):
        """Forcing should_include -> True twice yields the same (True, '')."""
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: True
        )
        first = cli_verify._check_full_pipeline(str(tmp_path))
        second = cli_verify._check_full_pipeline(str(tmp_path))
        assert first == (True, "")
        assert second == (True, "")


class TestVerifyFilterContract:
    """The surviving _verify_filter is a faithful bool projection."""

    def test_verify_filter_true_on_accept(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: True
        )
        f = ContentFilter()
        assert cli_verify._verify_filter(f, object()) is True

    def test_verify_filter_false_on_reject(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: False
        )
        f = ContentFilter()
        assert cli_verify._verify_filter(f, object()) is False

    def test_verify_filter_returns_bool_type(self, tmp_path, monkeypatch):
        """Return type must be a real bool, not a truthy int/str."""
        monkeypatch.setattr(
            ContentFilter, "should_include", lambda self, page: True
        )
        f = ContentFilter()
        result = cli_verify._verify_filter(f, object())
        assert type(result) is bool


class TestEndToEndCli:
    """End-to-end: the installed CLI verify command runs the full pipeline."""

    def test_cli_verify_runs(self, tmp_path):
        """`personal-index verify` (full) exits 0 on a clean temp data dir."""
        from click.testing import CliRunner

        from personal_index.cli import main

        runner = CliRunner(isolate_filesystem=False)
        result = runner.invoke(
            main, ["verify", "--data-dir", str(tmp_path)], catch_exceptions=False
        )
        assert result.exit_code == 0, (
            f"verify CLI failed (exit {result.exit_code}):\n{result.output}"
        )
        assert "checks passed" in result.output.lower()
