"""
Unit tests for core security utilities.
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)
from app.core.config import settings


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """Test that hash function returns a string."""
        result = get_password_hash("testpassword123")
        assert isinstance(result, str)

    def test_hash_password_contains_salt_separator(self):
        """Test that hash contains salt$hash format."""
        result = get_password_hash("testpassword123")
        assert "$" in result
        parts = result.split("$")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # salt is 16 bytes hex = 32 chars

    def test_hash_password_different_salts(self):
        """Test that same password produces different hashes."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hash_value = get_password_hash(password)
        assert verify_password(password, hash_value) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hash_value = get_password_hash(password)
        assert verify_password(wrong_password, hash_value) is False

    def test_verify_password_invalid_hash_format(self):
        """Test verifying password with invalid hash format."""
        assert verify_password("password", "invalid_hash_format") is False
        assert verify_password("password", "") is False
        assert verify_password("password", "no_separator") is False

    def test_verify_password_empty_password(self):
        """Test verifying empty password."""
        hash_value = get_password_hash("testpassword")
        assert verify_password("", hash_value) is False

    def test_hash_password_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@$$w0rd!#$%^&*()"
        hash_value = get_password_hash(password)
        assert verify_password(password, hash_value) is True

    def test_hash_password_unicode(self):
        """Test hashing password with unicode characters."""
        password = "пароль🔐"
        hash_value = get_password_hash(password)
        assert verify_password(password, hash_value) is True


class TestCreateAccessToken:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_string(self):
        """Test that token creation returns a string."""
        token = create_access_token(subject=1)
        assert isinstance(token, str)

    def test_create_access_token_with_user_id(self):
        """Test creating token with user ID."""
        user_id = 123
        token = create_access_token(subject=user_id)
        assert token is not None

    def test_create_access_token_with_string_subject(self):
        """Test creating token with string subject."""
        token = create_access_token(subject="user@example.com")
        assert isinstance(token, str)

    def test_create_access_token_custom_expiry(self):
        """Test creating token with custom expiry time."""
        expires_delta = timedelta(hours=2)
        token = create_access_token(subject=1, expires_delta=expires_delta)
        assert isinstance(token, str)

    def test_create_access_token_default_expiry(self):
        """Test creating token with default expiry."""
        token = create_access_token(subject=1)
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_create_access_token_contains_required_claims(self):
        """Test that token contains required JWT claims."""
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload


class TestDecodeToken:
    """Tests for JWT token decoding."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token(subject=123)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(subject=1, expires_delta=expired_delta)
        payload = decode_token(token)
        assert payload is None

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_empty_token(self):
        """Test decoding an empty token."""
        payload = decode_token("")
        assert payload is None

    def test_decode_tampered_token(self):
        """Test decoding a tampered token."""
        valid_token = create_access_token(subject=1)
        tampered = valid_token[:-5] + "XXXXX"
        payload = decode_token(tampered)
        assert payload is None

    def test_decode_token_wrong_algorithm(self):
        """Test decoding token with wrong algorithm."""
        import jwt
        from datetime import datetime, timezone, timedelta

        # Create token with wrong algorithm
        wrong_payload = {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "sub": "1",
            "type": "access",
        }
        wrong_token = jwt.encode(
            wrong_payload,
            settings.SECRET_KEY,
            algorithm="HS512",  # Different algorithm
        )
        payload = decode_token(wrong_token)
        assert payload is None


class TestTokenLifecycle:
    """Tests for complete token lifecycle."""

    def test_token_roundtrip(self):
        """Test creating and decoding a token."""
        user_id = 999
        token = create_access_token(subject=user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_token_expiry_accuracy(self):
        """Test token expiry is set correctly."""
        expires_delta = timedelta(minutes=30)
        token = create_access_token(subject=1, expires_delta=expires_delta)
        payload = decode_token(token)
        assert payload is not None

        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = (exp_datetime - now).total_seconds()

        # Should be approximately 30 minutes (allow 5 second tolerance)
        assert 1795 < diff < 1805
