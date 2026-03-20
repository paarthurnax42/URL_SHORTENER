"""
Unit tests for link CRUD operations.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.link import (
    create_link,
    get_by_short_code,
    get_by_alias,
    search_by_original,
    delete_link,
    update_link,
    get_stats,
    get_expired_links,
    get_unused_links,
    cleanup_old_links,
    is_owner,
    encode_id,
    decode_short_code,
)
from app.models.links import Link
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestCreateLink:
    """Tests for create_link function."""

    async def test_create_link_success(self, test_session: AsyncSession):
        """Test successful link creation."""
        link = await create_link(
            session=test_session,
            original="https://example.com/test",
        )

        assert link.original == "https://example.com/test"
        assert link.short is not None
        assert link.id is not None
        assert link.clicks_count == 0
        assert link.deleted_at is None

    async def test_create_link_with_alias(self, test_session: AsyncSession):
        """Test creating link with custom alias."""
        link = await create_link(
            session=test_session,
            original="https://example.com/aliased",
            alias="my-custom-alias",
        )

        assert link.alias == "my-custom-alias"

    async def test_create_link_duplicate_alias(self, test_session: AsyncSession):
        """Test creating link with duplicate alias raises error."""
        await create_link(
            session=test_session,
            original="https://example.com/first",
            alias="duplicate-alias",
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_link(
                session=test_session,
                original="https://example.com/second",
                alias="duplicate-alias",
            )

    async def test_create_link_duplicate_original(self, test_session: AsyncSession):
        """Test creating link with same original URL raises error."""
        await create_link(
            session=test_session,
            original="https://duplicate.com/url",
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_link(
                session=test_session,
                original="https://duplicate.com/url",
            )

    async def test_create_link_with_expiry(self, test_session: AsyncSession):
        """Test creating link with expiration time."""
        link = await create_link(
            session=test_session,
            original="https://example.com/expiring",
            expired_at=60,  # 60 minutes
        )

        assert link.expired_at is not None
        # Should be approximately 60 minutes from now
        now = datetime.now(timezone.utc)
        expired_at = link.expired_at
        # Handle both timezone-aware and naive datetimes
        if expired_at.tzinfo is None:
            expired_at = expired_at.replace(tzinfo=timezone.utc)
        diff = (expired_at - now).total_seconds()
        assert 3500 < diff < 3700  # ~60 minutes with tolerance

    async def test_create_link_with_owner(self, test_session: AsyncSession):
        """Test creating link with owner ID."""
        user = User(
            email="owner@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()

        link = await create_link(
            session=test_session,
            original="https://example.com/owned",
            owner_id=user.id,
        )

        assert link.owner_id == user.id

    async def test_create_link_short_code_unique(self, test_session: AsyncSession):
        """Test that each link gets unique short code."""
        link1 = await create_link(
            session=test_session,
            original="https://example.com/first",
        )
        link2 = await create_link(
            session=test_session,
            original="https://example.com/second",
        )

        assert link1.short != link2.short


@pytest.mark.asyncio
class TestGetByShortCode:
    """Tests for get_by_short_code function."""

    async def test_get_by_short_code_exists(self, test_session: AsyncSession):
        """Test getting link by existing short code."""
        link = await create_link(
            session=test_session,
            original="https://example.com/findme",
        )

        result = await get_by_short_code(test_session, link.short)

        assert result is not None
        assert result.id == link.id
        assert result.original == link.original

    async def test_get_by_short_code_not_exists(self, test_session: AsyncSession):
        """Test getting link by non-existent short code."""
        result = await get_by_short_code(test_session, "nonexistent")

        assert result is None

    async def test_get_by_short_code_deleted(self, test_session: AsyncSession):
        """Test getting deleted link returns None."""
        link = await create_link(
            session=test_session,
            original="https://example.com/deleted",
        )
        await delete_link(test_session, link)

        result = await get_by_short_code(test_session, link.short)

        assert result is None


@pytest.mark.asyncio
class TestGetByAlias:
    """Tests for get_by_alias function."""

    async def test_get_by_alias_exists(self, test_session: AsyncSession):
        """Test getting link by existing alias."""
        link = await create_link(
            session=test_session,
            original="https://example.com/aliased",
            alias="find-this-alias",
        )

        result = await get_by_alias(test_session, "find-this-alias")

        assert result is not None
        assert result.id == link.id

    async def test_get_by_alias_not_exists(self, test_session: AsyncSession):
        """Test getting link by non-existent alias."""
        result = await get_by_alias(test_session, "nonexistent-alias")

        assert result is None

    async def test_get_by_alias_deleted(self, test_session: AsyncSession):
        """Test getting deleted link by alias returns None."""
        link = await create_link(
            session=test_session,
            original="https://example.com/aliased-deleted",
            alias="deleted-alias",
        )
        await delete_link(test_session, link)

        result = await get_by_alias(test_session, "deleted-alias")

        assert result is None


@pytest.mark.asyncio
class TestSearchByOriginal:
    """Tests for search_by_original function."""

    async def test_search_exact_match(self, test_session: AsyncSession):
        """Test searching by exact URL match."""
        await create_link(
            session=test_session,
            original="https://example.com/search-test",
        )

        results = await search_by_original(
            test_session,
            "https://example.com/search-test",
        )

        assert len(results) == 1
        assert results[0].original == "https://example.com/search-test"

    async def test_search_partial_match(self, test_session: AsyncSession):
        """Test searching by partial URL match."""
        await create_link(
            session=test_session,
            original="https://example.com/partial-match-test",
        )

        results = await search_by_original(test_session, "example.com")

        assert len(results) >= 1

    async def test_search_case_insensitive(self, test_session: AsyncSession):
        """Test search is case-insensitive."""
        await create_link(
            session=test_session,
            original="https://EXAMPLE.com/CaseTest",
        )

        results = await search_by_original(test_session, "example.com")

        assert len(results) >= 1

    async def test_search_no_results(self, test_session: AsyncSession):
        """Test search with no matching results."""
        results = await search_by_original(
            test_session,
            "https://nonexistent-domain-xyz.com",
        )

        assert len(results) == 0

    async def test_search_deleted_excluded(self, test_session: AsyncSession):
        """Test search excludes deleted links."""
        link = await create_link(
            session=test_session,
            original="https://example.com/search-deleted",
        )
        await delete_link(test_session, link)

        results = await search_by_original(
            test_session,
            "https://example.com/search-deleted",
        )

        assert len(results) == 0


@pytest.mark.asyncio
class TestDeleteLink:
    """Tests for delete_link function."""

    async def test_delete_link_soft_delete(self, test_session: AsyncSession):
        """Test that delete is soft delete."""
        link = await create_link(
            session=test_session,
            original="https://example.com/to-delete",
        )

        await delete_link(test_session, link)

        assert link.deleted_at is not None

    async def test_delete_link_preserves_data(self, test_session: AsyncSession):
        """Test that soft delete preserves link data."""
        link = await create_link(
            session=test_session,
            original="https://example.com/preserved",
            alias="preserve-alias",
        )
        original_short = link.short

        await delete_link(test_session, link)

        assert link.short == original_short
        assert link.original == "https://example.com/preserved"
        assert link.alias == "preserve-alias"


@pytest.mark.asyncio
class TestUpdateLink:
    """Tests for update_link function."""

    async def test_update_original(self, test_session: AsyncSession):
        """Test updating original URL."""
        link = await create_link(
            session=test_session,
            original="https://example.com/original",
        )

        updated = await update_link(
            session=test_session,
            link=link,
            original="https://new-example.com/updated",
        )

        assert updated.original == "https://new-example.com/updated"

    async def test_update_alias(self, test_session: AsyncSession):
        """Test updating alias."""
        link = await create_link(
            session=test_session,
            original="https://example.com/original",
        )

        updated = await update_link(
            session=test_session,
            link=link,
            alias="new-alias",
        )

        assert updated.alias == "new-alias"

    async def test_update_expired_at(self, test_session: AsyncSession):
        """Test updating expiration time."""
        link = await create_link(
            session=test_session,
            original="https://example.com/expiring",
        )

        updated = await update_link(
            session=test_session,
            link=link,
            expired_at=120,
        )

        assert updated.expired_at is not None


@pytest.mark.asyncio
class TestIsOwner:
    """Tests for is_owner function."""

    async def test_is_owner_true(self, test_session: AsyncSession):
        """Test is_owner returns True for correct owner."""
        user = User(
            email="owner@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()

        link = await create_link(
            session=test_session,
            original="https://example.com/owned",
            owner_id=user.id,
        )

        assert is_owner(link, user.id) is True

    async def test_is_owner_false(self, test_session: AsyncSession):
        """Test is_owner returns False for wrong owner."""
        import uuid
        
        # Create a user first to satisfy FK constraint
        user = User(
            email=f"owner-test-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        link = await create_link(
            session=test_session,
            original="https://example.com/owned",
            owner_id=user.id,
        )

        assert is_owner(link, 999) is False

    async def test_is_owner_no_owner(self, test_session: AsyncSession):
        """Test is_owner returns False when no owner."""
        link = await create_link(
            session=test_session,
            original="https://example.com/no-owner",
        )

        assert is_owner(link, 1) is False


@pytest.mark.asyncio
class TestGetStats:
    """Tests for get_stats function."""

    async def test_get_stats_active_link(self, test_session: AsyncSession):
        """Test getting stats for active link."""
        link = await create_link(
            session=test_session,
            original="https://example.com/stats",
        )

        stats = await get_stats(link)

        assert stats["id"] == link.id
        assert stats["short"] == link.short
        assert stats["is_active"] is True

    async def test_get_stats_expired_link(self, test_session: AsyncSession):
        """Test getting stats for expired link."""
        link = await create_link(
            session=test_session,
            original="https://example.com/expired-stats",
            expired_at=1,  # 1 minute
        )

        # Manually set as expired for testing
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()

        stats = await get_stats(link)

        assert stats["is_active"] is False


@pytest.mark.asyncio
class TestGetExpiredLinks:
    """Tests for get_expired_links function."""

    async def test_get_expired_links_returns_expired(self, test_session: AsyncSession):
        """Test getting expired links."""
        link = await create_link(
            session=test_session,
            original="https://example.com/expired",
            expired_at=1,
        )
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()

        expired = await get_expired_links(test_session)

        assert len(expired) >= 1
        assert link.id in [l.id for l in expired]

    async def test_get_expired_links_excludes_active(self, test_session: AsyncSession):
        """Test that active links are not included."""
        link = await create_link(
            session=test_session,
            original="https://example.com/active",
        )

        expired = await get_expired_links(test_session)

        assert link.id not in [l.id for l in expired]


@pytest.mark.asyncio
class TestGetUnusedLinks:
    """Tests for get_unused_links function."""

    async def test_get_unused_links_returns_unused(self, test_session: AsyncSession):
        """Test getting unused links."""
        link = await create_link(
            session=test_session,
            original="https://example.com/unused",
        )
        # Set created_at to 31 days ago
        link.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        link.last_used_at = None
        await test_session.commit()

        unused = await get_unused_links(test_session, days=30)

        assert len(unused) >= 1
        assert link.id in [l.id for l in unused]


@pytest.mark.asyncio
class TestCleanupOldLinks:
    """Tests for cleanup_old_links function."""

    async def test_cleanup_old_links_marks_deleted(self, test_session: AsyncSession):
        """Test that cleanup marks links as deleted."""
        link = await create_link(
            session=test_session,
            original="https://example.com/old-unused",
        )
        link.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        link.last_used_at = None
        await test_session.commit()

        count = await cleanup_old_links(test_session, days=30)

        assert count >= 1
        assert link.deleted_at is not None
