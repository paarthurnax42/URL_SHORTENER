"""
Unit tests for Redis cache utilities.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import RedisLinkCache


class TestRedisLinkCache:
    """Tests for Redis link cache operations."""

    def test_cache_initialization(self):
        """Test cache initializes with correct attributes."""
        cache = RedisLinkCache()
        assert cache._redis is None
        assert cache._prefix == "link:"

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting cache values."""
        mock_redis = AsyncMock()
        mock_data = {}
        
        async def mock_set(key, value, ex=None):
            mock_data[key] = value
            
        async def mock_get(key):
            return mock_data.get(key)
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        link_data = {
            "id": 1,
            "original": "https://example.com",
            "short": "abc123",
        }

        await cache.set("abc123", link_data)
        result = await cache.get("abc123")

        assert result == link_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns None."""
        mock_redis = AsyncMock()
        
        async def mock_get(key):
            return None
        
        mock_redis.get = mock_get
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting cache values."""
        mock_redis = AsyncMock()
        mock_data = {"link:abc123": {"id": 1}}
        
        async def mock_delete(key):
            mock_data.pop(key, None)
        
        mock_redis.delete = mock_delete
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        await cache.delete("abc123")
        assert "link:abc123" not in mock_data

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test deleting nonexistent key doesn't raise error."""
        mock_redis = AsyncMock()
        
        async def mock_delete(key):
            pass
        
        mock_redis.delete = mock_delete
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        await cache.delete("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """Test setting cache value with TTL."""
        captured_ex = None
        mock_redis = AsyncMock()
        
        async def mock_set(key, value, ex=None):
            nonlocal captured_ex
            captured_ex = ex
        
        mock_redis.set = mock_set
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        await cache.set("key", {"id": 1}, ttl=7200)
        assert captured_ex == 7200

    @pytest.mark.asyncio
    async def test_get_without_connection(self):
        """Test get returns None when not connected."""
        cache = RedisLinkCache()
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_without_connection(self):
        """Test set does nothing when not connected."""
        cache = RedisLinkCache()
        await cache.set("key", {"id": 1})  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_without_connection(self):
        """Test delete does nothing when not connected."""
        cache = RedisLinkCache()
        await cache.delete("key")  # Should not raise

    @pytest.mark.asyncio
    async def test_cache_serializes_datetime(self):
        """Test that cache properly handles datetime serialization."""
        mock_redis = AsyncMock()
        mock_data = {}
        
        async def mock_set(key, value, ex=None):
            mock_data[key] = json.dumps(value, default=str)
            
        async def mock_get(key):
            val = mock_data.get(key)
            if val:
                return json.loads(val)
            return None
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        link_data = {
            "id": 1,
            "created_at": datetime.now().isoformat(),
        }

        await cache.set("key", link_data)
        result = await cache.get("key")

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_cache_key_prefix(self):
        """Test that cache uses correct key prefix."""
        captured_key = None
        mock_redis = AsyncMock()
        
        async def mock_set(key, value, ex=None):
            nonlocal captured_key
            captured_key = key
        
        mock_redis.set = mock_set
        
        cache = RedisLinkCache()
        cache._redis = mock_redis

        await cache.set("testkey", {"id": 1})
        assert captured_key == "link:testkey"

    @pytest.mark.asyncio
    async def test_stats_without_connection(self):
        """Test stats returns default when not connected."""
        cache = RedisLinkCache()
        stats = await cache.get_stats()
        assert stats == {"size": 0, "connected": False}
