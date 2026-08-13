"""Tests for password hashing and verification."""

from personal_index.auth.passwords import (
    PasswordConfig,
    hash_password,
    is_valid_password,
    verify_password,
)


class TestPasswordConfig:
    def test_defaults(self):
        c = PasswordConfig()
        assert c.algorithm == "sha256"
        assert c.iterations == 100_000
        assert c.salt_length == 32
        assert c.key_length == 32

    def test_custom(self):
        c = PasswordConfig(algorithm="sha512", iterations=50_000)
        assert c.algorithm == "sha512"
        assert c.iterations == 50_000


class TestHashPassword:
    def test_hash_format(self):
        h = hash_password("Test123!")
        parts = h.split("$")
        assert len(parts) == 4
        assert parts[0] == "sha256"

    def test_hash_different_each_time(self):
        h1 = hash_password("Test123!")
        h2 = hash_password("Test123!")
        assert h1 != h2

    def test_hash_same_password_verifies(self):
        h = hash_password("Test123!")
        assert verify_password("Test123!", h) is True

    def test_hash_wrong_password_fails(self):
        h = hash_password("Test123!")
        assert verify_password("Wrong123!", h) is False

    def test_hash_custom_config(self):
        config = PasswordConfig(iterations=1_000)
        h = hash_password("Test123!", config)
        parts = h.split("$")
        assert parts[1] == "1000"


class TestVerifyPassword:
    def test_verify_valid(self):
        h = hash_password("SecurePass1!")
        assert verify_password("SecurePass1!", h) is True

    def test_verify_invalid(self):
        h = hash_password("SecurePass1!")
        assert verify_password("other", h) is False

    def test_verify_bad_format(self):
        assert verify_password("test", "badformat") is False

    def test_verify_empty_hash(self):
        assert verify_password("test", "") is False

    def test_verify_malformed_parts(self):
        assert verify_password("test", "a$b$c") is False

    def test_verify_non_int_iterations(self):
        assert verify_password("test", "sha256$notint$salt$hash") is False


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
        valid, errors = is_valid_password("NoDigitHere!")
        assert valid is False
        assert any("digit" in e for e in errors)

    def test_no_special(self):
        valid, errors = is_valid_password("NoSpecial1")
        assert valid is False
        assert any("special" in e for e in errors)

    def test_multiple_errors(self):
        valid, errors = is_valid_password("abc")
        assert valid is False
        assert len(errors) >= 3

    def test_custom_min_length(self):
        valid, errors = is_valid_password("Ab1!Test", min_length=20)
        assert valid is False
        assert any("20" in e for e in errors)

    def test_empty_password(self):
        valid, errors = is_valid_password("")
        assert valid is False
        assert len(errors) >= 2
