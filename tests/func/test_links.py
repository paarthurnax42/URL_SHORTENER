"""
Functional API tests for link endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
class TestCreateShortLink:
    """Tests for POST /api/v1/links/shorten endpoint."""

    async def test_create_link_success(self, authorized_client: AsyncClient):
        """Test successful link creation."""
        link_data = {
            "original": "https://example.com/test-link",
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["original"] == link_data["original"]
        assert "short" in data
        assert "id" in data
        assert data["alias"] is None

    async def test_create_link_with_alias(self, authorized_client: AsyncClient):
        """Test creating link with custom alias."""
        link_data = {
            "original": "https://example.com/aliased-link",
            "alias": "my-custom-alias",
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["alias"] == "my-custom-alias"

    async def test_create_link_with_expiry(self, authorized_client: AsyncClient):
        """Test creating link with expiration time."""
        link_data = {
            "original": "https://example.com/expiring-link",
            "expired_at": 60,  # 60 minutes
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expired_at"] is not None

    async def test_create_link_duplicate_alias(
        self,
        authorized_client: AsyncClient,
        test_link_with_alias: dict,
    ):
        """Test creating link with duplicate alias returns 400."""
        link_data = {
            "original": "https://example.com/another-link",
            "alias": test_link_with_alias.alias,
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_link_invalid_url(self, authorized_client: AsyncClient):
        """Test creating link with invalid URL."""
        link_data = {
            "original": "not-a-valid-url",
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 422

    async def test_create_link_unauthenticated(self, client: AsyncClient):
        """Test creating link without authentication (should still work)."""
        link_data = {
            "original": "https://example.com/public-link",
        }

        response = await client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        # Unauthenticated users can create links (owner_id will be None)
        assert response.status_code == 201

    async def test_create_link_duplicate_original(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test creating duplicate link returns 400."""
        link_data = {
            "original": test_link.original,
        }

        response = await authorized_client.post(
            "/api/v1/links/shorten",
            json=link_data,
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestGetLinkInfo:
    """Tests for GET /api/v1/links/{short_code}/info endpoint."""

    async def test_get_link_info_by_short_code(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test getting link info by short code."""
        response = await client.get(f"/api/v1/links/{test_link.short}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_link.id
        assert data["short"] == test_link.short

    async def test_get_link_info_by_alias(
        self,
        client: AsyncClient,
        test_link_with_alias: dict,
    ):
        """Test getting link info by alias."""
        response = await client.get(
            f"/api/v1/links/{test_link_with_alias.alias}/info"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_link_with_alias.id

    async def test_get_link_info_not_found(self, client: AsyncClient):
        """Test getting non-existent link returns 404."""
        response = await client.get("/api/v1/links/nonexistent/info")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteLink:
    """Tests for DELETE /api/v1/links/{short_code} endpoint."""

    async def test_delete_link_success(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test successful link deletion."""
        response = await authorized_client.delete(
            f"/api/v1/links/{test_link.short}"
        )

        assert response.status_code == 204

        # Verify link is deleted
        get_response = await authorized_client.get(
            f"/api/v1/links/{test_link.short}/info"
        )
        assert get_response.status_code == 404

    async def test_delete_link_not_owner(
        self,
        authorized_client: AsyncClient,
    ):
        """Test deleting link owned by another user returns 403."""
        # Create a link with a different owner
        from app.models.links import Link
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.db.session import async_session_maker

        async with async_session_maker() as session:
            other_user = User(
                email="other@example.com",
                password_hash=get_password_hash("password"),
            )
            session.add(other_user)
            await session.commit()

            other_link = Link(
                original="https://example.com/other-link",
                short="other123",
                owner_id=other_user.id,
            )
            session.add(other_link)
            await session.commit()
            other_link_id = other_link.id

        response = await authorized_client.delete("/api/v1/links/other123")

        assert response.status_code == 403

    async def test_delete_link_not_found(
        self,
        authorized_client: AsyncClient,
    ):
        """Test deleting non-existent link returns 404."""
        response = await authorized_client.delete("/api/v1/links/nonexistent")

        assert response.status_code == 404

    async def test_delete_link_unauthenticated(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test deleting link without authentication returns 401."""
        response = await client.delete(f"/api/v1/links/{test_link.short}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateLink:
    """Tests for PUT /api/v1/links/{short_code} endpoint."""

    async def test_update_link_original(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test updating link original URL."""
        update_data = {
            "original": "https://new-example.com/updated",
        }

        response = await authorized_client.put(
            f"/api/v1/links/{test_link.short}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["original"] == update_data["original"]

    async def test_update_link_alias(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test updating link alias."""
        update_data = {
            "alias": "new-alias",
        }

        response = await authorized_client.put(
            f"/api/v1/links/{test_link.short}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alias"] == "new-alias"

    async def test_update_link_not_owner(
        self,
        authorized_client: AsyncClient,
    ):
        """Test updating link owned by another user returns 403."""
        from app.models.links import Link
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.db.session import async_session_maker

        async with async_session_maker() as session:
            other_user = User(
                email="other2@example.com",
                password_hash=get_password_hash("password"),
            )
            session.add(other_user)
            await session.commit()

            other_link = Link(
                original="https://example.com/other-link2",
                short="other456",
                owner_id=other_user.id,
            )
            session.add(other_link)
            await session.commit()

        update_data = {"original": "https://hacked.com"}
        response = await authorized_client.put(
            "/api/v1/links/other456",
            json=update_data,
        )

        assert response.status_code == 403

    async def test_update_link_not_found(
        self,
        authorized_client: AsyncClient,
    ):
        """Test updating non-existent link returns 404."""
        update_data = {"original": "https://new.com"}
        response = await authorized_client.put(
            "/api/v1/links/nonexistent",
            json=update_data,
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetStats:
    """Tests for GET /api/v1/links/{short_code}/stats endpoint."""

    async def test_get_stats_success(
        self,
        client: AsyncClient,
        test_link: dict,
    ):
        """Test getting link statistics."""
        response = await client.get(f"/api/v1/links/{test_link.short}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "short" in data
        assert "clicks_count" in data
        assert "is_active" in data

    async def test_get_stats_not_found(self, client: AsyncClient):
        """Test getting stats for non-existent link."""
        response = await client.get("/api/v1/links/nonexistent/stats")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetMyLinks:
    """Tests for GET /api/v1/links/my endpoint."""

    async def test_get_my_links_success(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test getting current user's links."""
        response = await authorized_client.get("/api/v1/links/my")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert test_link.id in [link["id"] for link in data]

    async def test_get_my_links_unauthenticated(self, client: AsyncClient):
        """Test getting links without authentication returns 401."""
        response = await client.get("/api/v1/links/my")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestSearchLinks:
    """Tests for GET /api/v1/links/search endpoint."""

    async def test_search_links_success(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test searching links by URL."""
        response = await authorized_client.get(
            f"/api/v1/links/search?original_url={test_link.original}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_search_links_no_results(
        self,
        authorized_client: AsyncClient,
    ):
        """Test searching with no matching results."""
        response = await authorized_client.get(
            "/api/v1/links/search?original_url=https://nonexistent-xyz.com"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_search_links_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test searching without authentication returns 401."""
        response = await client.get("/api/v1/links/search?original_url=test.com")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestExpiredLinks:
    """Tests for GET /api/v1/links/expired/history endpoint."""

    async def test_get_expired_links_success(
        self,
        authorized_client: AsyncClient,
        test_expired_link: dict,
    ):
        """Test getting expired links."""
        response = await authorized_client.get("/api/v1/links/expired/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_expired_links_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test getting expired links without authentication."""
        response = await client.get("/api/v1/links/expired/history")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestCleanupUnusedLinks:
    """Tests for POST /api/v1/links/cleanup/unused endpoint."""

    async def test_cleanup_unused_links_success(
        self,
        authorized_client: AsyncClient,
    ):
        """Test cleaning up unused links."""
        response = await authorized_client.post(
            "/api/v1/links/cleanup/unused",
            params={"days": 30},
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert "days_threshold" in data

    async def test_cleanup_unused_links_unauthenticated(
        self,
        client: AsyncClient,
    ):
        """Test cleanup without authentication returns 401."""
        response = await client.post("/api/v1/links/cleanup/unused")

        assert response.status_code == 401
