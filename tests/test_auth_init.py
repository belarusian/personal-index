"""Tests for personal_index.auth.__init__."""

import personal_index.auth


class TestAuthInit:
    def test_all_is_sorted(self):
        """TICKET-68: __all__ must be sorted alphabetically (RUF022)."""
        assert personal_index.auth.__all__ == sorted(personal_index.auth.__all__)

    def test_all_contains_expected_exports(self):
        expected = {
            "JWTManager", "TokenPayload", "generate_token", "verify_token",
            "APIKeyStore", "APIKey", "validate_api_key",
            "Permission", "Role", "PermissionChecker",
            "hash_password", "verify_password", "PasswordConfig",
            "SessionStore", "Session",
        }
        assert set(personal_index.auth.__all__) == expected

    def test_all_exports_are_accessible(self):
        """All items in __all__ should be importable from the module."""
        for name in personal_index.auth.__all__:
            assert hasattr(personal_index.auth, name), f"Missing export: {name}"
