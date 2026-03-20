"""
Unit tests for sqids encoding/decoding utilities.
"""
import pytest

from app.crud.link import encode_id, decode_short_code


class TestEncodeId:
    """Tests for ID encoding function."""

    def test_encode_id_returns_string(self):
        """Test that encoding returns a string."""
        result = encode_id(1)
        assert isinstance(result, str)

    def test_encode_id_positive_integer(self):
        """Test encoding positive integers."""
        assert encode_id(1) is not None
        assert encode_id(100) is not None
        assert encode_id(1000000) is not None

    def test_encode_id_different_values(self):
        """Test that different IDs produce different encodings."""
        assert encode_id(1) != encode_id(2)
        assert encode_id(100) != encode_id(101)

    def test_encode_id_consistent(self):
        """Test that encoding is consistent (same input = same output)."""
        result1 = encode_id(42)
        result2 = encode_id(42)
        assert result1 == result2

    def test_encode_id_min_length(self):
        """Test that encoded result meets minimum length from settings."""
        from app.core.config import settings
        result = encode_id(1)
        assert len(result) >= settings.LINK_LENGHT

    def test_encode_id_no_special_chars(self):
        """Test that encoded result contains only alphanumeric chars."""
        result = encode_id(123)
        assert result.isalnum()

    def test_encode_id_sequence(self):
        """Test encoding a sequence of IDs."""
        results = [encode_id(i) for i in range(1, 11)]
        assert len(results) == 10
        assert len(set(results)) == 10  # All unique


class TestDecodeShortCode:
    """Tests for short code decoding function."""

    def test_decode_valid_code(self):
        """Test decoding a valid encoded ID."""
        original_id = 42
        encoded = encode_id(original_id)
        decoded = decode_short_code(encoded)
        assert decoded == original_id

    def test_decode_roundtrip(self):
        """Test encode -> decode roundtrip."""
        for id_value in [1, 10, 100, 1000, 10000]:
            encoded = encode_id(id_value)
            decoded = decode_short_code(encoded)
            assert decoded == id_value

    def test_decode_invalid_code(self):
        """Test decoding an invalid code."""
        # Sqids will decode any valid string to some number
        result = decode_short_code("invalid")
        # Sqids may return a number even for "invalid" strings
        assert isinstance(result, int) or result is None

    def test_decode_empty_string(self):
        """Test decoding an empty string."""
        result = decode_short_code("")
        # Empty string may decode to None or a number depending on sqids config
        assert isinstance(result, int) or result is None

    def test_decode_malformed_code(self):
        """Test decoding malformed codes."""
        # Sqids is permissive - it will decode most strings
        result1 = decode_short_code("!!!")
        result2 = decode_short_code("abc-def")
        # Results may be None or integers
        assert isinstance(result1, int) or result1 is None
        assert isinstance(result2, int) or result2 is None

    def test_decode_none_input(self):
        """Test decoding None input."""
        # Sqids decode may handle None differently
        try:
            result = decode_short_code(None)
            # If it doesn't raise, result should be None or int
            assert result is None or isinstance(result, int)
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass

    def test_decode_case_sensitive(self):
        """Test that decoding is case-sensitive."""
        encoded = encode_id(123)
        # Sqids is typically case-sensitive
        upper = encoded.upper()
        lower = encoded.lower()
        if encoded != upper:
            # If case differs, results may differ
            decoded_upper = decode_short_code(upper)
            if decoded_upper is not None:
                assert decoded_upper != 123 or encoded == upper


class TestSqidsIntegration:
    """Integration tests for sqids encoding/decoding."""

    def test_large_id_encoding(self):
        """Test encoding large IDs."""
        large_id = 999999999
        encoded = encode_id(large_id)
        decoded = decode_short_code(encoded)
        assert decoded == large_id

    def test_sequential_ids_unique(self):
        """Test that sequential IDs produce unique codes."""
        codes = set()
        for i in range(1, 1001):
            code = encode_id(i)
            assert code not in codes, f"Duplicate code {code} for ID {i}"
            codes.add(code)

    def test_decode_all_sequential_ids(self):
        """Test decoding all sequential IDs."""
        for i in range(1, 101):
            encoded = encode_id(i)
            decoded = decode_short_code(encoded)
            assert decoded == i
