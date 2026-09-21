"""Adversarial deep tests for APIKeyStore.validate_key naive ``expires_at`` handling.

QA-64: ``validate_key`` parses ``api_key.expires_at`` with
``datetime.fromisoformat`` and compares ``exp < datetime.now(timezone.utc)``.
The ``datetime.now(timezone.utc)`` on the right is UTC-**aware**. A *naive* ISO
``expires_at`` (no ``+00:00`` / ``Z`` suffix) is a valid ISO format per the
``create_key`` docstring ("ISO format expiration datetime") and parses
successfully, but ``naive < aware`` raises ``TypeError``. The ``except`` clause
catches only ``ValueError`` (unparseable), NOT ``TypeError`` (naive-vs-aware),
so the exception propagates out of ``validate_key`` instead of the key being
treated as expired (aware past -> None) or valid (aware future -> key).

This is the same naive-vs-aware datetime seam class as QA-62
(content_archive.archive_old, fixed) and QA-63 (sitemap.get_recent_entries +
progress.elapsed_seconds, OPEN). The auth/api_keys.py:106 site is a NEW,
previously-unfiled member of that class.

The xfail-strict pin documents the defect; the armor pins pin the already-correct
aware / no-expiration paths so a future fix cannot regress them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from personal_index.auth.api_keys import APIKeyStore


def _past_naive_iso() -> str:
    """A naive ISO timestamp ~6 years in the past (no tz suffix)."""
    return (datetime.now(timezone.utc) - timedelta(days=2190)).replace(tzinfo=None).isoformat()


def _future_naive_iso() -> str:
    """A naive ISO timestamp ~1 day in the future (no tz suffix)."""
    return (datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None).isoformat()


def _past_aware_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=2190)).isoformat()


def _future_aware_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


class TestValidateKeyNaiveExpiresAt:
    def test_naive_past_expires_at_is_treated_expired(self):
        """QA-64: a naive ISO expires_at in the past is a valid ISO format and
        must be treated as expired (return None), matching the aware-past path.
        Instead it raises TypeError (naive < aware) which the except clause does
        not catch. See tickets/QA-64.md."""
        store = APIKeyStore()
        raw, _ = store.create_key(owner="alice", expires_at=_past_naive_iso())
        # Contract: expired key -> None (same as the aware-past path below).
        assert store.validate_key(raw) is None

    def test_naive_future_expires_at_is_treated_valid(self):
        """QA-64: a naive ISO expires_at in the future is a valid ISO format and
        must be treated as valid (return the key), matching the aware-future
        path. Instead it raises TypeError (naive < aware). See tickets/QA-64.md."""
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice", expires_at=_future_naive_iso())
        result = store.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id

    # --- Armor: the already-correct paths (must stay green) ---

    def test_aware_past_expires_at_is_expired(self):
        """Armor: an aware ISO expires_at in the past is correctly expired."""
        store = APIKeyStore()
        raw, _ = store.create_key(owner="alice", expires_at=_past_aware_iso())
        assert store.validate_key(raw) is None

    def test_aware_future_expires_at_is_valid(self):
        """Armor: an aware ISO expires_at in the future is correctly valid."""
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice", expires_at=_future_aware_iso())
        result = store.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id

    def test_no_expires_at_is_valid(self):
        """Armor: a key with no expires_at is valid."""
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice")
        result = store.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id

    def test_unparseable_expires_at_is_valid(self):
        """Armor: an unparseable expires_at (ValueError) is swallowed and the
        key is treated as valid (existing behavior)."""
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice", expires_at="not-a-date")
        result = store.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id
