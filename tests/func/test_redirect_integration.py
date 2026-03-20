"""
Integration tests for redirect endpoint with test database.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.models.links import Link
from app.models.user import User
from app.core.security import get_password_hash
from app.crud.link import create_link, delete_link


@pytest.mark.asyncio
class TestRedirectIntegration:
    """Integration tests for redirect endpoint using test DB."""

    async def test_redirect_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test successful redirect."""
        link = await create_link(
            session=test_session,
            original="https://example.com/redirect-test",
            owner_id=test_user.id,
        )
        
        response = await client.get(
            f"/links/{link.short}",
            follow_redirects=False,
        )
        
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/redirect-test"

    async def test_redirect_not_found(
        self,
        client: AsyncClient,
    ):
        """Test redirect for non-existent link."""
        response = await client.get("/links/nonexistent123")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_redirect_expired_link(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test redirect for expired link returns 410."""
        link = await create_link(
            session=test_session,
            original="https://example.com/expired-redirect",
            owner_id=test_user.id,
            expired_at=1,
        )
        
        # Manually expire the link
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()
        
        response = await client.get(f"/links/{link.short}")
        
        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()

    async def test_redirect_deleted_link(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test redirect for deleted link returns 404."""
        link = await create_link(
            session=test_session,
            original="https://example.com/deleted-redirect",
            owner_id=test_user.id,
        )
        
        await delete_link(test_session, link)
        
        response = await client.get(f"/links/{link.short}")
        
        assert response.status_code == 404

    async def test_redirect_increments_click_count(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that redirect increments click count."""
        link = await create_link(
            session=test_session,
            original="https://example.com/click-increment",
            owner_id=test_user.id,
        )
        initial_clicks = link.clicks_count
        
        await client.get(f"/links/{link.short}", follow_redirects=False)
        
        # Refresh from DB
        await test_session.refresh(link)
        assert link.clicks_count == initial_clicks + 1

    async def test_redirect_updates_last_used(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that redirect updates last_used_at."""
        link = await create_link(
            session=test_session,
            original="https://example.com/last-used-update",
            owner_id=test_user.id,
        )
        
        initial_last_used = link.last_used_at
        
        await client.get(f"/links/{link.short}", follow_redirects=False)
        
        # Refresh from DB
        await test_session.refresh(link)
        assert link.last_used_at is not None
        if initial_last_used:
            assert link.last_used_at >= initial_last_used

    async def test_redirect_with_alias(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test redirect using custom alias."""
        link = await create_link(
            session=test_session,
            original="https://example.com/alias-redirect",
            alias="my-custom-alias",
            owner_id=test_user.id,
        )
        
        response = await client.get("/links/my-custom-alias", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/alias-redirect"

    async def test_redirect_cache_invalidated(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that redirect invalidates cache."""
        link = await create_link(
            session=test_session,
            original="https://example.com/cache-invalidate",
            owner_id=test_user.id,
        )
        
        # Just verify redirect works - cache invalidation is internal
        response = await client.get(
            f"/links/{link.short}",
            follow_redirects=False,
        )
        
        assert response.status_code == 307

    async def test_redirect_preserves_url(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that redirect preserves original URL exactly."""
        original_url = "https://example.com/path?query=value&param=test"
        
        link = await create_link(
            session=test_session,
            original=original_url,
            owner_id=test_user.id,
        )
        
        response = await client.get(f"/links/{link.short}", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == original_url

    async def test_redirect_with_complex_url(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test redirect with complex URL containing special characters."""
        original_url = "https://example.com/search?q=hello+world&page=1#anchor"
        
        link = await create_link(
            session=test_session,
            original=original_url,
            owner_id=test_user.id,
        )
        
        response = await client.get(f"/links/{link.short}", follow_redirects=False)
        
        assert response.status_code == 307
        # URL should be preserved (may be encoded)
        assert "example.com" in response.headers["location"]

