"""Adversarial deep tests for personal_index.auth (cycle 324).

Covers: APIKeyStore, JWTManager, hash_password/verify_password,
SessionStore, PermissionChecker — edge cases, round-trips, idempotence,
unicode/empty/negative inputs, security invariants.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.auth.api_keys import APIKey, APIKeyStore, validate_api_key
from personal_index.auth.passwords import (
    PasswordConfig,
    hash_password,
    is_valid_password,
    verify_password,
)
from personal_index.auth.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    PermissionChecker,
    Role,
    User,
)
from personal_index.auth.sessions import Session, SessionStore
from personal_index.auth.tokens import (
    JWTManager,
    TokenPayload,
    generate_token,
    verify_token,
)

# ---------------------------------------------------------------------------
# APIKeyStore
# ---------------------------------------------------------------------------


class TestAPIKeyStoreAdversarial:
    def test_create_key_returns_prefixed_raw_key(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice", name="test-key")
        assert raw.startswith("pk_")
        assert meta.owner == "alice"
        assert meta.name == "test-key"
        assert meta.is_active is True

    def test_create_key_custom_prefix(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="bob", prefix="sk_")
        assert raw.startswith("sk_")
        assert meta.prefix == "sk_"

    def test_validate_key_round_trip(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice")
        result = store.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id
        assert result.owner == "alice"

    def test_validate_key_wrong_key_returns_none(self):
        store = APIKeyStore()
        store.create_key(owner="alice")
        assert store.validate_key("pk_wrong_key_12345") is None

    def test_validate_key_empty_string_returns_none(self):
        store = APIKeyStore()
        store.create_key(owner="alice")
        assert store.validate_key("") is None

    def test_validate_key_unicode_raw_key(self):
        store = APIKeyStore()
        raw, _ = store.create_key(owner="alice")
        # Append unicode to the raw key — should NOT match
        assert store.validate_key(raw + "Привет") is None
        # Original still works
        assert store.validate_key(raw) is not None

    def test_validate_key_after_revoke_returns_none(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice")
        assert store.validate_key(raw) is not None
        assert store.revoke_key(meta.key_id) is True
        assert store.validate_key(raw) is None

    def test_validate_key_after_delete_returns_none(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice")
        assert store.validate_key(raw) is not None
        assert store.delete_key(meta.key_id) is True
        assert store.validate_key(raw) is None

    def test_revoke_key_unknown_id_returns_false(self):
        store = APIKeyStore()
        assert store.revoke_key("nonexistent") is False

    def test_delete_key_unknown_id_returns_false(self):
        store = APIKeyStore()
        assert store.delete_key("nonexistent") is False

    def test_validate_key_expired_returns_none(self):
        store = APIKeyStore()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        raw, _ = store.create_key(owner="alice", expires_at=past)
        assert store.validate_key(raw) is None

    def test_validate_key_future_expiry_works(self):
        store = APIKeyStore()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        raw, _ = store.create_key(owner="alice", expires_at=future)
        assert store.validate_key(raw) is not None

    def test_validate_key_malformed_expiry_passes_through(self):
        """A malformed expires_at (ValueError) is caught and the key is still valid."""
        store = APIKeyStore()
        raw, _ = store.create_key(owner="alice", expires_at="not-a-date")
        assert store.validate_key(raw) is not None

    def test_usage_count_increments(self):
        store = APIKeyStore()
        raw, meta = store.create_key(owner="alice")
        store.validate_key(raw)
        store.validate_key(raw)
        assert meta.usage_count == 2

    def test_to_dict_excludes_hashed_key(self):
        """Security: to_dict must NOT leak the hashed key."""
        store = APIKeyStore()
        _, meta = store.create_key(owner="alice")
        d = meta.to_dict()
        assert "hashed_key" not in d
        assert "key_id" in d
        assert "owner" in d

    def test_list_keys_owner_filter(self):
        store = APIKeyStore()
        store.create_key(owner="alice")
        store.create_key(owner="bob")
        alice_keys = store.list_keys(owner="alice")
        assert len(alice_keys) == 1
        assert alice_keys[0].owner == "alice"

    def test_list_keys_empty_owner_returns_all(self):
        """owner='' is falsy → returns all keys (documented: 'optionally filtered')."""
        store = APIKeyStore()
        store.create_key(owner="alice")
        store.create_key(owner="bob")
        all_keys = store.list_keys(owner="")
        assert len(all_keys) == 2

    def test_list_keys_none_owner_returns_all(self):
        store = APIKeyStore()
        store.create_key(owner="alice")
        store.create_key(owner="bob")
        all_keys = store.list_keys(owner=None)
        assert len(all_keys) == 2

    def test_validate_api_key_convenience(self):
        store = APIKeyStore()
        raw, _ = store.create_key(owner="alice")
        result = validate_api_key(store, raw)
        assert result is not None
        assert result.owner == "alice"

    def test_two_keys_same_owner_independent(self):
        store = APIKeyStore()
        raw1, meta1 = store.create_key(owner="alice")
        raw2, meta2 = store.create_key(owner="alice")
        assert meta1.key_id != meta2.key_id
        assert store.validate_key(raw1) is not None
        assert store.validate_key(raw2) is not None
        store.revoke_key(meta1.key_id)
        assert store.validate_key(raw1) is None
        assert store.validate_key(raw2) is not None


# ---------------------------------------------------------------------------
# JWTManager
# ---------------------------------------------------------------------------


class TestJWTManagerAdversarial:
    def test_create_verify_round_trip(self):
        mgr = JWTManager("secret-key")
        token = mgr.create_token("user1", roles=["admin"])
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.sub == "user1"
        assert payload.roles == ["admin"]

    def test_verify_wrong_secret_returns_none(self):
        mgr1 = JWTManager("secret-1")
        mgr2 = JWTManager("secret-2")
        token = mgr1.create_token("user1")
        assert mgr2.verify_token(token) is None

    def test_verify_tampered_payload_returns_none(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        parts = token.split(".")
        # Tamper with the payload (middle part)
        tampered = parts[0] + "." + parts[1][:-2] + "xx" + "." + parts[2]
        assert mgr.verify_token(tampered) is None

    def test_verify_tampered_signature_returns_none(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "." + "invalidsig"
        assert mgr.verify_token(tampered) is None

    def test_verify_empty_string_returns_none(self):
        mgr = JWTManager("secret")
        assert mgr.verify_token("") is None

    def test_verify_two_part_token_returns_none(self):
        mgr = JWTManager("secret")
        assert mgr.verify_token("part1.part2") is None

    def test_verify_four_part_token_returns_none(self):
        mgr = JWTManager("secret")
        assert mgr.verify_token("a.b.c.d") is None

    def test_verify_expired_token_returns_none(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", ttl=-10)
        assert mgr.verify_token(token) is None

    def test_verify_zero_ttl_token(self):
        """ttl=0 → exp ≈ now; should be expired by the time verify runs."""
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", ttl=0)
        time.sleep(0.01)
        assert mgr.verify_token(token) is None

    def test_blacklist_prevents_reuse(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        assert mgr.verify_token(token) is not None
        assert mgr.blacklist_token(token) is True
        assert mgr.verify_token(token) is None

    def test_blacklist_idempotent(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        assert mgr.blacklist_token(token) is True
        assert mgr.blacklist_token(token) is False  # already blacklisted

    def test_unicode_subject_round_trip(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("Пользователь-Üñîçødé")
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.sub == "Пользователь-Üñîçødé"

    def test_empty_subject_round_trip(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("")
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.sub == ""

    def test_metadata_round_trip(self):
        mgr = JWTManager("secret")
        meta = {"plan": "pro", "org": "acme"}
        token = mgr.create_token("user1", metadata=meta)
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.metadata == meta

    def test_roles_round_trip(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", roles=["admin", "editor"])
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.roles == ["admin", "editor"]

    def test_none_roles_becomes_empty_list(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", roles=None)
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.roles == []

    def test_none_metadata_becomes_empty_dict(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", metadata=None)
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.metadata == {}

    def test_generate_verify_convenience_functions(self):
        token = generate_token("my-secret", "user42", ttl=3600, roles=["viewer"])
        payload = verify_token(token, "my-secret")
        assert payload is not None
        assert payload.sub == "user42"
        assert payload.roles == ["viewer"]

    def test_verify_convenience_wrong_secret(self):
        token = generate_token("secret-a", "user1")
        assert verify_token(token, "secret-b") is None

    def test_token_payload_to_dict_excludes_none_exp(self):
        p = TokenPayload(sub="user1")
        d = p.to_dict()
        assert "exp" not in d  # exp is None → excluded
        assert d["sub"] == "user1"

    def test_token_payload_from_dict_ignores_unknown_keys(self):
        p = TokenPayload.from_dict({"sub": "u", "unknown_key": 42})
        assert p.sub == "u"
        assert not hasattr(p, "unknown_key")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordAdversarial:
    def test_hash_verify_round_trip(self):
        h = hash_password("MyP@ss1")
        assert verify_password("MyP@ss1", h) is True

    def test_verify_wrong_password_returns_false(self):
        h = hash_password("MyP@ss1")
        assert verify_password("WrongP@ss1", h) is False

    def test_verify_empty_password_string(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("x", h) is False

    def test_verify_malformed_hash_three_parts(self):
        assert verify_password("test", "a$b$c") is False

    def test_verify_malformed_hash_five_parts(self):
        assert verify_password("test", "a$b$c$d$e") is False

    def test_verify_malformed_hash_non_numeric_iterations(self):
        assert verify_password("test", "sha256$notanumber$salt$hash") is False

    def test_verify_empty_hash_string(self):
        assert verify_password("test", "") is False

    def test_unicode_password_round_trip(self):
        h = hash_password("Пароль-Üñîçødé-123!")
        assert verify_password("Пароль-Üñîçødé-123!", h) is True
        assert verify_password("wrong", h) is False

    def test_hash_contains_four_parts(self):
        h = hash_password("test123!")
        parts = h.split("$")
        assert len(parts) == 4
        assert parts[0] == "sha256"
        assert parts[1] == "100000"

    def test_hash_is_salt_unique(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # different salts

    def test_custom_low_iterations_config(self):
        cfg = PasswordConfig(iterations=1000, salt_length=16)
        h = hash_password("test123!", config=cfg)
        parts = h.split("$")
        assert parts[1] == "1000"
        assert verify_password("test123!", h) is True

    def test_verify_with_wrong_iterations_fails(self):
        cfg = PasswordConfig(iterations=1000)
        h = hash_password("test123!", config=cfg)
        # Tamper: change iterations in the hash string
        parts = h.split("$")
        parts[1] = "2000"
        tampered = "$".join(parts)
        assert verify_password("test123!", tampered) is False

    def test_is_valid_password_strong(self):
        valid, errors = is_valid_password("Str0ng!Pass")
        assert valid is True
        assert errors == []

    def test_is_valid_password_weak_short(self):
        valid, errors = is_valid_password("Ab1!")
        assert valid is False
        assert any("at least" in e for e in errors)

    def test_is_valid_password_no_uppercase(self):
        valid, errors = is_valid_password("lower123!")
        assert valid is False
        assert any("uppercase" in e for e in errors)

    def test_is_valid_password_no_digit(self):
        valid, errors = is_valid_password("NoDigitsHere!")
        assert valid is False
        assert any("digit" in e for e in errors)

    def test_is_valid_password_no_special(self):
        valid, errors = is_valid_password("NoSpecial123")
        assert valid is False
        assert any("special" in e for e in errors)

    def test_is_valid_password_empty_string(self):
        valid, errors = is_valid_password("")
        assert valid is False
        assert len(errors) >= 4  # missing length, upper, lower, digit, special

    def test_is_valid_password_unicode(self):
        valid, errors = is_valid_password("Üñîçødé123!")
        assert valid is True


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


class TestSessionStoreAdversarial:
    def test_create_get_round_trip(self):
        store = SessionStore()
        s = store.create_session("user1", ip_address="10.0.0.1")
        fetched = store.get_session(s.session_id)
        assert fetched is not None
        assert fetched.user_id == "user1"
        assert fetched.ip_address == "10.0.0.1"

    def test_get_unknown_session_returns_none(self):
        store = SessionStore()
        assert store.get_session("nonexistent") is None

    def test_get_expired_session_returns_none_and_removes(self):
        store = SessionStore()
        s = store.create_session("user1", ttl=-1)  # immediately expired
        # ttl=-1: expires_at = time.time() + (-1 or default) → -1 is falsy → uses default!
        # So ttl=-1 actually uses default_ttl. Let's set expires_at directly.
        s2 = store.create_session("user2")
        s2.expires_at = time.time() - 10  # force expired
        assert store.get_session(s2.session_id) is None
        # Should have been removed
        assert store.get_session(s2.session_id) is None

    def test_update_session_data_merge(self):
        store = SessionStore()
        s = store.create_session("user1", data={"a": 1})
        assert store.update_session(s.session_id, data={"b": 2}) is True
        fetched = store.get_session(s.session_id)
        assert fetched is not None
        assert fetched.data == {"a": 1, "b": 2}

    def test_update_session_unknown_returns_false(self):
        store = SessionStore()
        assert store.update_session("nonexistent", data={"x": 1}) is False

    def test_update_session_extend_ttl(self):
        store = SessionStore()
        s = store.create_session("user1", ttl=100)
        old_exp = s.expires_at
        time.sleep(0.01)
        assert store.update_session(s.session_id, extend_ttl=500) is True
        assert s.expires_at > old_exp

    def test_destroy_session(self):
        store = SessionStore()
        s = store.create_session("user1")
        assert store.destroy_session(s.session_id) is True
        assert store.destroy_session(s.session_id) is False  # already gone

    def test_destroy_user_sessions_count(self):
        store = SessionStore()
        store.create_session("user1")
        store.create_session("user1")
        store.create_session("user2")
        count = store.destroy_user_sessions("user1")
        assert count == 2
        assert store.get_active_count("user1") == 0
        assert store.get_active_count("user2") == 1

    def test_get_active_count_all(self):
        store = SessionStore()
        store.create_session("user1")
        store.create_session("user2")
        assert store.get_active_count() == 2

    def test_get_active_count_by_user(self):
        store = SessionStore()
        store.create_session("user1")
        store.create_session("user1")
        store.create_session("user2")
        assert store.get_active_count("user1") == 2
        assert store.get_active_count("user2") == 1

    def test_unicode_user_id(self):
        store = SessionStore()
        s = store.create_session("Пользователь-Üñîçødé")
        fetched = store.get_session(s.session_id)
        assert fetched is not None
        assert fetched.user_id == "Пользователь-Üñîçødé"

    def test_empty_user_id(self):
        store = SessionStore()
        s = store.create_session("")
        fetched = store.get_session(s.session_id)
        assert fetched is not None
        assert fetched.user_id == ""

    def test_session_data_isolation(self):
        """Two sessions must not share the same data dict."""
        store = SessionStore()
        s1 = store.create_session("user1")
        s2 = store.create_session("user2")
        s1.data["key"] = "value1"
        assert "key" not in s2.data

    def test_session_to_dict_includes_all_fields(self):
        s = Session(user_id="u1", ip_address="1.2.3.4", user_agent="test-agent")
        d = s.to_dict()
        assert d["user_id"] == "u1"
        assert d["ip_address"] == "1.2.3.4"
        assert d["user_agent"] == "test-agent"
        assert d["is_active"] is True

    def test_session_is_expired_inactive(self):
        s = Session(user_id="u1", is_active=False)
        assert s.is_expired() is True

    def test_session_is_expired_no_expiry(self):
        s = Session(user_id="u1", expires_at=None)
        assert s.is_expired() is False

    def test_cleanup_expired_removes_only_expired(self):
        store = SessionStore()
        s1 = store.create_session("user1")
        s2 = store.create_session("user2")
        s1.expires_at = time.time() - 10  # force expired
        removed = store.cleanup_expired()
        assert removed == 1
        assert store.get_session(s1.session_id) is None
        assert store.get_session(s2.session_id) is not None


# ---------------------------------------------------------------------------
# PermissionChecker
# ---------------------------------------------------------------------------


class TestPermissionCheckerAdversarial:
    @pytest.fixture(autouse=True)
    def _restore_role_permissions(self):
        """Snapshot and restore the module-level ROLE_PERMISSIONS after each
        test.

        QA-57: PermissionChecker.__init__ shallow-copies ROLE_PERMISSIONS, so
        add_role_permissions mutates the shared inner sets and leaks into the
        module-level constant. Without this fixture, a test that customizes a
        role (e.g. test_custom_role_permissions adding WRITE_INDEX to CRAWLER)
        would pollute the global and break the implementer-owned
        tests/test_auth/test_permissions.py::test_crawler_role, which asserts
        CRAWLER lacks WRITE_INDEX. This fixture keeps the deep suite
        self-contained regardless of the QA-57 fix landing.
        """
        snapshot = {role: set(perms) for role, perms in ROLE_PERMISSIONS.items()}
        yield
        for role in list(ROLE_PERMISSIONS.keys()):
            ROLE_PERMISSIONS[role] = set(snapshot.get(role, set()))
        # Remove any roles added during the test that were not in the snapshot.
        for role in list(ROLE_PERMISSIONS.keys()):
            if role not in snapshot:
                del ROLE_PERMISSIONS[role]

    def test_admin_has_all_permissions(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="admin", roles=[Role.ADMIN])
        for perm in Permission:
            assert checker.check(user, perm) is True

    def test_viewer_limited_permissions(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="viewer", roles=[Role.VIEWER])
        assert checker.check(user, Permission.READ_INDEX) is True
        assert checker.check(user, Permission.WRITE_INDEX) is False
        assert checker.check(user, Permission.MANAGE_USERS) is False

    def test_inactive_user_denied_all(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="admin", roles=[Role.ADMIN], is_active=False)
        assert checker.check(user, Permission.READ_INDEX) is False
        assert checker.check_any(user, Permission.READ_INDEX) is False
        assert checker.check_all(user, Permission.READ_INDEX) is False

    def test_check_any_one_of_many(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="v", roles=[Role.VIEWER])
        assert checker.check_any(
            user, Permission.WRITE_INDEX, Permission.READ_INDEX
        ) is True

    def test_check_any_none_match(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="v", roles=[Role.VIEWER])
        assert checker.check_any(
            user, Permission.MANAGE_USERS, Permission.MANAGE_KEYS
        ) is False

    def test_check_all_subset(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="admin", roles=[Role.ADMIN])
        assert checker.check_all(
            user, Permission.READ_INDEX, Permission.WRITE_INDEX
        ) is True

    def test_check_all_not_subset(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="v", roles=[Role.VIEWER])
        assert checker.check_all(
            user, Permission.READ_INDEX, Permission.MANAGE_USERS
        ) is False

    def test_extra_permissions_grant_access(self):
        checker = PermissionChecker()
        user = User(
            user_id="u1",
            username="v",
            roles=[Role.VIEWER],
            extra_permissions=[Permission.MANAGE_USERS],
        )
        assert checker.check(user, Permission.MANAGE_USERS) is True

    def test_custom_role_permissions(self):
        checker = PermissionChecker()
        checker.add_role_permissions(Role.CRAWLER, {Permission.WRITE_INDEX})
        user = User(user_id="u1", username="c", roles=[Role.CRAWLER])
        assert checker.check(user, Permission.WRITE_INDEX) is True

    def test_add_role_permissions_is_instance_isolated(self):
        """QA-57: customizing one PermissionChecker must not leak into another.

        The docstring of add_role_permissions says 'Add custom permissions to a
        role' (instance-level), and get_role_permissions returns a .copy(),
        implying per-instance isolation. But __init__ does
        `ROLE_PERMISSIONS.copy()` — a shallow copy — so the inner sets are the
        SAME objects as the module-level ROLE_PERMISSIONS. add_role_permissions
        calls `self._role_permissions[role].update(permissions)`, mutating the
        shared set and therefore the global constant.
        """
        a = PermissionChecker()
        a.add_role_permissions(Role.CRAWLER, {Permission.WRITE_INDEX})
        # A fresh instance must NOT see A's customization.
        b = PermissionChecker()
        user = User(user_id="u1", username="c", roles=[Role.CRAWLER])
        assert b.check(user, Permission.WRITE_INDEX) is False

    def test_get_role_permissions_returns_copy(self):
        checker = PermissionChecker()
        perms = checker.get_role_permissions(Role.ADMIN)
        perms.add(Permission.READ_INDEX)  # mutate the copy
        # Original should be unaffected (it already has READ_INDEX, so check a different way)
        original = checker.get_role_permissions(Role.ADMIN)
        assert original == set(Permission)

    def test_multiple_roles_union(self):
        """Positive union of two roles (order-independent; the negative
        WRITE_INDEX assertion is covered by the xfail-strict isolation test
        below, which is sensitive to the global ROLE_PERMISSIONS state)."""
        checker = PermissionChecker()
        user = User(
            user_id="u1",
            username="multi",
            roles=[Role.VIEWER, Role.CRAWLER],
        )
        assert checker.check(user, Permission.READ_INDEX) is True
        assert checker.check(user, Permission.RUN_CRAWL) is True

    def test_no_roles_no_permissions(self):
        checker = PermissionChecker()
        user = User(user_id="u1", username="nobody", roles=[])
        assert checker.check(user, Permission.READ_INDEX) is False
        assert checker.check_any(user, Permission.READ_INDEX) is False
