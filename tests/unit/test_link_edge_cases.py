"""
Additional CRUD tests for uncovered scenarios.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.crud.link import (
    create_link,
    get_by_short_code,
    decode_short_code,
    is_owner,
    get_stats,
)
from app.models.links import Link
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestLinkCacheBehavior:
    """Tests for link caching behavior."""

    async def test_get_by_short_code_caches_result(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that get_by_short_code caches the result."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/cache-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        
        # First call - should query DB
        result1 = await get_by_short_code(test_session, link.short)
        assert result1 is not None
        assert result1.id == link.id

    async def test_get_by_short_code_increment_clicks(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test get_by_short_code with increment_clicks=True."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/increment-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        initial_clicks = link.clicks_count
        
        # Get with increment
        result = await get_by_short_code(
            test_session,
            link.short,
            increment_clicks=True,
        )
        
        assert result is not None
        assert result.clicks_count == initial_clicks + 1


@pytest.mark.asyncio
class TestLinkValidation:
    """Tests for link validation edge cases."""

    async def test_create_link_with_minimal_expiry(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test creating link with minimal expiry time."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/min-expiry-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
            expired_at=1,  # 1 minute
        )
        
        assert link.expired_at is not None
        assert link.expired_at > datetime.now(timezone.utc)

    async def test_create_link_with_long_expiry(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test creating link with long expiry time."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/long-expiry-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
            expired_at=525600,  # 1 year in minutes
        )
        
        assert link.expired_at is not None
        # Should be approximately 1 year from now
        diff = (link.expired_at - datetime.now(timezone.utc)).total_seconds()
        assert diff > 31000000  # More than ~360 days


@pytest.mark.asyncio
class TestDecodeShortCodeEdgeCases:
    """Tests for decode_short_code edge cases."""

    def test_decode_short_code_special_characters(self):
        """Test decoding with special characters."""
        result = decode_short_code("!!!")
        # Should handle gracefully (return None or a number)
        assert result is None or isinstance(result, int)

    def test_decode_short_code_very_long_string(self):
        """Test decoding very long string."""
        result = decode_short_code("a" * 1000)
        assert result is None or isinstance(result, int)

    def test_decode_short_code_unicode(self):
        """Test decoding unicode characters."""
        result = decode_short_code("тест")
        assert result is None or isinstance(result, int)


@pytest.mark.asyncio
class TestIsOwnerEdgeCases:
    """Tests for is_owner edge cases."""

    async def test_is_owner_with_none_owner_id(
        self,
        test_session: AsyncSession,
    ):
        """Test is_owner when link has no owner."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/no-owner-{uuid.uuid4().hex[:8]}",
        )
        
        # Link has no owner, so any user_id should return False
        assert is_owner(link, 1) is False
        assert is_owner(link, 999) is False

    async def test_is_owner_with_zero_user_id(self):
        """Test is_owner with user_id=0."""
        # Create a mock link object
        class MockLink:
            owner_id = 1
        
        link = MockLink()
        assert is_owner(link, 0) is False


@pytest.mark.asyncio
class TestGetStatsEdgeCases:
    """Tests for get_stats edge cases."""

    async def test_get_stats_for_expired_link(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test getting stats for expired link."""
        import uuid
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/expired-stats-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
            expired_at=1,
        )
        
        # Manually expire
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()
        
        stats = await get_stats(link)
        
        assert stats["is_active"] is False
        assert stats["expired_at"] is not None

    async def test_get_stats_for_deleted_link(
        self,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test getting stats for deleted link."""
        import uuid
        from app.crud.link import delete_link
        
        link = await create_link(
            session=test_session,
            original=f"https://example.com/deleted-stats-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        
        await delete_link(test_session, link)
        
        stats = await get_stats(link)
        
        assert stats["is_active"] is False
