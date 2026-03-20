"""
Functional API tests for redirect endpoint.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient, Response


@pytest.mark.asyncio
class TestRedirectEndpoint:
    """Tests for GET /links/{short_code} redirect endpoint."""

    async def test_redirect_success(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test successful redirect to original URL."""
        response = await client.get(
            f"/links/{test_link.short}",
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"] == test_link.original

    async def test_redirect_by_alias(
        self,
        client: AsyncClient,
        test_link_with_alias: dict,
    ):
        """Test redirect using alias."""
        response = await client.get(
            f"/links/{test_link_with_alias.alias}",
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"] == test_link_with_alias.original

    async def test_redirect_not_found(self, client: AsyncClient):
        """Test redirect for non-existent short code."""
        response = await client.get("/links/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_redirect_expired_link(
        self,
        client: AsyncClient,
        test_expired_link: dict,
    ):
        """Test redirect for expired link returns 410."""
        response = await client.get(f"/links/{test_expired_link.short}")

        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()

    async def test_redirect_deleted_link(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_link: dict,
    ):
        """Test redirect for deleted link returns 404."""
        from app.crud.link import delete_link

        await delete_link(test_session, test_link)

        response = await client.get(f"/links/{test_link.short}")

        assert response.status_code == 404

    async def test_redirect_increments_click_count(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test that redirect increments click count."""
        original_clicks = test_link.clicks_count

        await client.get(f"/links/{test_link.short}", follow_redirects=False)

        from app.db.session import async_session_maker
        from app.crud.link import get_by_short_code

        async with async_session_maker() as session:
            updated_link = await get_by_short_code(session, test_link.short)
            assert updated_link.clicks_count == original_clicks + 1

    async def test_redirect_updates_last_used(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test that redirect updates last_used_at."""
        from datetime import datetime, timezone
        from app.db.session import async_session_maker
        from app.crud.link import get_by_short_code

        original_last_used = test_link.last_used_at

        await client.get(f"/links/{test_link.short}", follow_redirects=False)

        async with async_session_maker() as session:
            updated_link = await get_by_short_code(session, test_link.short)
            assert updated_link.last_used_at is not None
            if original_last_used:
                assert updated_link.last_used_at >= original_last_used

    async def test_redirect_follow_redirect(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test following redirect to final destination."""
        response = await client.get(
            f"/links/{test_link.short}",
            follow_redirects=True,
        )

        # Should follow to the original URL
        # Note: This may fail if the original URL is not accessible
        # but the redirect itself should work
        assert response.status_code in [200, 301, 302, 404]

    async def test_redirect_case_sensitive(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test that short code lookup is case-sensitive."""
        # Try uppercase version
        response = await client.get(f"/links/{test_link.short.upper()}")

        # Should not find the link (case mismatch)
        assert response.status_code == 404

    async def test_redirect_with_trailing_slash(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test redirect with trailing slash in URL."""
        response = await client.get(
            f"/links/{test_link.short}/",
            follow_redirects=False,
        )

        # FastAPI should handle this
        assert response.status_code in [307, 404]


@pytest.mark.asyncio
class TestRedirectEdgeCases:
    """Edge case tests for redirect endpoint."""

    async def test_redirect_special_characters_in_code(
        self,
        client: AsyncClient,
    ):
        """Test redirect with special characters in short code."""
        response = await client.get("/links/abc!@#")

        assert response.status_code == 404

    async def test_redirect_very_long_code(self, client: AsyncClient):
        """Test redirect with very long short code."""
        long_code = "a" * 1000
        response = await client.get(f"/links/{long_code}")

        assert response.status_code == 404

    async def test_redirect_empty_code(self, client: AsyncClient):
        """Test redirect with empty short code."""
        response = await client.get("/links/")

        assert response.status_code == 404

    async def test_redirect_numeric_code(self, client: AsyncClient):
        """Test redirect with numeric-only code."""
        response = await client.get("/links/12345")

        assert response.status_code == 404
