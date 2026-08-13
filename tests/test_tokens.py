"""Tests for JWT token management."""

import time

from personal_index.auth.tokens import (
    JWTManager,
    TokenPayload,
    generate_token,
    verify_token,
)


class TestTokenPayload:
    def test_to_dict(self):
        p = TokenPayload(sub="user1")
        d = p.to_dict()
        assert d["sub"] == "user1"
        assert "exp" not in d

    def test_to_dict_with_exp(self):
        p = TokenPayload(sub="user1", exp=time.time() + 3600)
        d = p.to_dict()
        assert "exp" in d

    def test_from_dict(self):
        d = {"sub": "user1", "iat": 12345, "jti": "abc"}
        p = TokenPayload.from_dict(d)
        assert p.sub == "user1"


class TestJWTManager:
    def test_create_and_verify(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.sub == "user1"

    def test_verify_wrong_secret(self):
        mgr1 = JWTManager("secret1")
        mgr2 = JWTManager("secret2")
        token = mgr1.create_token("user1")
        payload = mgr2.verify_token(token)
        assert payload is None

    def test_expired_token(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", ttl=0)
        time.sleep(0.1)
        payload = mgr.verify_token(token)
        assert payload is None

    def test_blacklist_token(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        assert mgr.blacklist_token(token) is True
        assert mgr.verify_token(token) is None

    def test_blacklist_already_blacklisted(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        mgr.blacklist_token(token)
        assert mgr.blacklist_token(token) is False

    def test_roles(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", roles=["admin"])
        payload = mgr.verify_token(token)
        assert payload is not None
        assert "admin" in payload.roles

    def test_metadata(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1", metadata={"ip": "1.2.3.4"})
        payload = mgr.verify_token(token)
        assert payload is not None
        assert payload.metadata["ip"] == "1.2.3.4"

    def test_malformed_token(self):
        mgr = JWTManager("secret")
        assert mgr.verify_token("not.a.valid.token.format.extra") is None

    def test_tampered_token(self):
        mgr = JWTManager("secret")
        token = mgr.create_token("user1")
        parts = token.split(".")
        parts[1] = "tampered"
        assert mgr.verify_token(".".join(parts)) is None


class TestConvenienceFunctions:
    def test_generate_and_verify(self):
        token = generate_token("secret", "user1", ttl=3600)
        payload = verify_token(token, "secret")
        assert payload is not None
        assert payload.sub == "user1"

    def test_generate_with_roles(self):
        token = generate_token("secret", "user1", roles=["editor"])
        payload = verify_token(token, "secret")
        assert payload is not None
        assert "editor" in payload.roles
