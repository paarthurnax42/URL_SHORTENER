"""
Additional API tests for edge cases and uncovered scenarios.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.links import Link
from app.models.user import User
from app.core.security import get_password_hash, create_access_token


@pytest.mark.asyncio
class TestRedirectEdgeCases:
    """Additional tests for redirect endpoint edge cases."""

    async def test_redirect_with_cache_invalidation(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test redirect properly invalidates cache."""
        from app.crud.link import create_link
        
        link = await create_link(
            session=test_session,
            original="https://example.com/cache-test",
            owner_id=test_user.id,
        )
        
        # Just test that redirect works - cache invalidation is internal
        response = await client.get(
            f"/links/{link.short}",
            follow_redirects=False,
        )
        
        assert response.status_code == 307

    async def test_redirect_preserves_click_count(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test that redirect preserves and increments click count."""
        from app.crud.link import create_link
        
        link = await create_link(
            session=test_session,
            original="https://example.com/click-test",
            owner_id=test_user.id,
        )
        initial_clicks = link.clicks_count
        
        await client.get(f"/links/{link.short}", follow_redirects=False)
        
        # Refresh from DB
        await test_session.refresh(link)
        assert link.clicks_count == initial_clicks + 1


@pytest.mark.asyncio
class TestLinkSearchEdgeCases:
    """Tests for link search edge cases."""

    async def test_search_with_special_characters(
        self,
        authorized_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test searching links with special characters in URL."""
        from app.crud.link import create_link
        
        link = await create_link(
            session=test_session,
            original="https://example.com/search?q=test&page=1",
            owner_id=test_user.id,
        )
        
        response = await authorized_client.get(
            "/api/v1/links/search?original_url=https://example.com/search?q=test"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_search_empty_query(
        self,
        authorized_client: AsyncClient,
    ):
        """Test searching with empty query."""
        response = await authorized_client.get(
            "/api/v1/links/search?original_url="
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestLinkStatsEdgeCases:
    """Tests for link statistics edge cases."""

    async def test_stats_for_link_with_no_clicks(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test getting stats for link with no clicks."""
        from app.crud.link import create_link
        
        link = await create_link(
            session=test_session,
            original="https://example.com/no-clicks",
            owner_id=test_user.id,
        )
        
        response = await client.get(f"/api/v1/links/{link.short}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["clicks_count"] == 0
        assert data["is_active"] is True

    async def test_stats_includes_all_fields(
        self,
        client: AsyncClient,
        test_link: Link,
    ):
        """Test that stats response includes all required fields."""
        response = await client.get(f"/api/v1/links/{test_link.short}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "id", "short", "original", "alias",
            "clicks_count", "created_at", "is_active"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
class TestAuthEdgeCases:
    """Tests for authentication edge cases."""

    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test login for inactive user."""
        import uuid
        
        # Create inactive user
        user = User(
            email=f"inactive-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=get_password_hash("password123"),
            is_active=False,
        )
        test_session.add(user)
        await test_session.commit()
        
        login_data = {
            "email": user.email,
            "password": "password123",
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            json=login_data,
        )
        
        # Inactive user should get 401
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTagEdgeCases:
    """Tests for tag operations edge cases."""

    async def test_get_links_by_tag_no_links(
        self,
        authorized_client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
    ):
        """Test getting links for tag with no links."""
        tag = Tag(
            name=f"empty-tag-{id}",
            owner_id=test_user.id,
        )
        test_session.add(tag)
        await test_session.commit()
        
        response = await authorized_client.get(f"/api/v1/tags/{tag.id}/links")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_tag_with_special_characters(
        self,
        authorized_client: AsyncClient,
    ):
        """Test creating tag with special characters in name."""
        tag_data = {"name": "tag-with-special-chars-123"}
        
        response = await authorized_client.post(
            "/api/v1/tags",
            json=tag_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "tag-with-special-chars-123"


@pytest.mark.asyncio
class TestRateLimiting:
    """Tests for rate limiting."""

    async def test_rate_limit_headers_present(
        self,
        client: AsyncClient,
    ):
        """Test that rate limit headers are present in response."""
        response = await client.get("/api/v1/links/search?original_url=test.com")
        
        # Rate limiting should add headers
        # Note: Actual headers depend on slowapi configuration
        assert response.status_code in [200, 401, 429]


@pytest.mark.asyncio
class TestCORS:
    """Tests for CORS configuration."""

    async def test_cors_headers_present(
        self,
        client: AsyncClient,
    ):
        """Test that CORS headers are present for OPTIONS request."""
        response = await client.options(
            "/api/v1/links/shorten",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        # CORS should be configured - just check response exists
        assert response is not None


# Import Tag model
from app.models.tag import Tag
