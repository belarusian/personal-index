"""Tests for password hashing and verification."""

from __future__ import annotations

from personal_index.auth.passwords import (
    PasswordConfig,
    hash_password,
    is_valid_password,
    verify_password,
)


class TestHashPassword:
    def test_hash_returns_string(self):
        h = hash_password("mysecretpassword")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_format(self):
        h = hash_password("mysecretpassword")
        parts = h.split("$")
        assert len(parts) == 4
        assert parts[0] == "sha256"

    def test_hash_is_deterministic_with_salt(self):
        h = hash_password("mysecretpassword")
        parts = h.split("$")
        _algorithm, iterations, salt, password_hash = parts
        # Same password + same salt = same hash
        from personal_index.auth.passwords import _hash_with_salt
        h2 = _hash_with_salt("mysecretpassword", salt, int(iterations))
        assert h2 == password_hash

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_password_different_hashes(self):
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2  # Different salts

    def test_custom_config(self):
        config = PasswordConfig(iterations=1000, salt_length=16)
        h = hash_password("password", config=config)
        parts = h.split("$")
        assert parts[1] == "1000"


class TestVerifyPassword:
    def test_verify_correct_password(self):
        h = hash_password("correctpassword")
        assert verify_password("correctpassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correctpassword")
        assert verify_password("wrongpassword", h) is False

    def test_verify_empty_password(self):
        h = hash_password("password")
        assert verify_password("", h) is False

    def test_verify_malformed_hash(self):
        assert verify_password("password", "malformed") is False

    def test_verify_hash_with_different_iterations(self):
        config = PasswordConfig(iterations=1000)
        h = hash_password("password", config=config)
        assert verify_password("password", h) is True

    def test_verify_unicode_password(self):
        h = hash_password("пароль123!@#")
        assert verify_password("пароль123!@#", h) is True


class TestIsValidPassword:
    def test_strong_password(self):
        valid, errors = is_valid_password("Str0ng!Pass")
        assert valid is True
        assert errors == []

    def test_too_short(self):
        valid, errors = is_valid_password("Ab1!")
        assert valid is False
        assert any("at least" in e for e in errors)

    def test_no_uppercase(self):
        valid, errors = is_valid_password("lowercase1!")
        assert valid is False
        assert any("uppercase" in e for e in errors)

    def test_no_lowercase(self):
        valid, errors = is_valid_password("UPPERCASE1!")
        assert valid is False
        assert any("lowercase" in e for e in errors)

    def test_no_digit(self):
        valid, errors = is_valid_password("NoDigits!!")
        assert valid is False
        assert any("digit" in e for e in errors)

    def test_no_special_char(self):
        valid, errors = is_valid_password("NoSpecial1")
        assert valid is False
        assert any("special" in e for e in errors)

    def test_multiple_errors(self):
        valid, errors = is_valid_password("abc")
        assert valid is False
        assert len(errors) >= 3

    def test_custom_min_length(self):
        valid, _errors = is_valid_password("Ab1!", min_length=10)
        assert valid is False
