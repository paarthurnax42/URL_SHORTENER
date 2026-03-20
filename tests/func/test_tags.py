"""
Functional API tests for tag endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCreateTag:
    """Tests for POST /api/v1/tags endpoint."""

    async def test_create_tag_success(
        self,
        authorized_client: AsyncClient,
        sample_tag_data: dict,
    ):
        """Test successful tag creation."""
        response = await authorized_client.post(
            "/api/v1/tags",
            json=sample_tag_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_tag_data["name"]
        assert "id" in data
        assert "created_at" in data

    async def test_create_tag_duplicate(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test creating duplicate tag returns 400."""
        duplicate_data = {"name": test_tag.name}

        response = await authorized_client.post(
            "/api/v1/tags",
            json=duplicate_data,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_tag_case_insensitive(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test tag name uniqueness is case-insensitive."""
        duplicate_data = {"name": test_tag.name.upper()}

        response = await authorized_client.post(
            "/api/v1/tags",
            json=duplicate_data,
        )

        assert response.status_code == 400

    async def test_create_tag_invalid_name(
        self,
        authorized_client: AsyncClient,
    ):
        """Test creating tag with invalid name."""
        invalid_data = {"name": ""}  # Empty name

        response = await authorized_client.post(
            "/api/v1/tags",
            json=invalid_data,
        )

        assert response.status_code == 422

    async def test_create_tag_name_too_long(
        self,
        authorized_client: AsyncClient,
    ):
        """Test creating tag with name too long."""
        invalid_data = {"name": "a" * 51}  # Max is 50

        response = await authorized_client.post(
            "/api/v1/tags",
            json=invalid_data,
        )

        assert response.status_code == 422

    async def test_create_tag_unauthenticated(self, client: AsyncClient):
        """Test creating tag without authentication returns 401."""
        response = await client.post(
            "/api/v1/tags",
            json={"name": "unauth-tag"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetMyTags:
    """Tests for GET /api/v1/tags endpoint."""

    async def test_get_my_tags_success(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test getting current user's tags."""
        response = await authorized_client.get("/api/v1/tags")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert test_tag.id in [tag["id"] for tag in data]

    async def test_get_my_tags_unauthenticated(self, client: AsyncClient):
        """Test getting tags without authentication returns 401."""
        response = await client.get("/api/v1/tags")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeleteTag:
    """Tests for DELETE /api/v1/tags/{tag_id} endpoint."""

    async def test_delete_tag_success(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test successful tag deletion."""
        response = await authorized_client.delete(f"/api/v1/tags/{test_tag.id}")

        assert response.status_code == 204

        # Verify tag is deleted
        get_response = await authorized_client.get("/api/v1/tags")
        tags = get_response.json()
        assert test_tag.id not in [tag["id"] for tag in tags]

    async def test_delete_tag_not_found(
        self,
        authorized_client: AsyncClient,
    ):
        """Test deleting non-existent tag returns 404."""
        response = await authorized_client.delete("/api/v1/tags/99999")

        assert response.status_code == 404

    async def test_delete_tag_unauthenticated(
        self,
        client: AsyncClient,
        test_tag: dict,
    ):
        """Test deleting tag without authentication returns 401."""
        response = await client.delete(f"/api/v1/tags/{test_tag.id}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetLinksByTag:
    """Tests for GET /api/v1/tags/{tag_id}/links endpoint."""

    async def test_get_links_by_tag_success(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test getting links by tag."""
        # First add tag to a link
        from app.db.session import async_session_maker
        from app.crud.link import create_link
        from app.crud.tag import add_tag_to_link

        async with async_session_maker() as session:
            link = await create_link(
                session=session,
                original="https://example.com/tagged-test",
                owner_id=test_tag.owner_id,
            )
            await add_tag_to_link(session, link, test_tag)
            link_short = link.short

        response = await authorized_client.get(f"/api/v1/tags/{test_tag.id}/links")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_links_by_tag_not_found(
        self,
        authorized_client: AsyncClient,
    ):
        """Test getting links for non-existent tag."""
        response = await authorized_client.get("/api/v1/tags/99999/links")

        assert response.status_code == 404

    async def test_get_links_by_tag_unauthenticated(
        self,
        client: AsyncClient,
        test_tag: dict,
    ):
        """Test getting links by tag without authentication."""
        response = await client.get(f"/api/v1/tags/{test_tag.id}/links")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTagLinkAssociation:
    """Tests for tag-link association endpoints."""

    async def test_add_tag_to_link_success(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
        test_link: dict,
    ):
        """Test adding tag to link."""
        response = await authorized_client.post(
            f"/api/v1/links/{test_link.short}/tags/{test_tag.id}",
        )

        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert data["message"] == "Tag added successfully"

    async def test_add_tag_to_link_not_found(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test adding tag to non-existent link."""
        response = await authorized_client.post(
            "/api/v1/links/nonexistent/tags/{}".format(test_tag.id),
        )

        assert response.status_code == 404

    async def test_remove_tag_from_link_success(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
        test_link: dict,
    ):
        """Test removing tag from link."""
        # First add the tag
        await authorized_client.post(
            f"/api/v1/links/{test_link.short}/tags/{test_tag.id}",
        )

        # Then remove it
        response = await authorized_client.delete(
            f"/api/v1/links/{test_link.short}/tags/{test_tag.id}",
        )

        assert response.status_code == 204

    async def test_remove_tag_from_link_not_found(
        self,
        authorized_client: AsyncClient,
        test_tag: dict,
    ):
        """Test removing tag from non-existent link."""
        response = await authorized_client.delete(
            "/api/v1/links/nonexistent/tags/{}".format(test_tag.id),
        )

        assert response.status_code == 404

    async def test_add_tag_not_owned_by_user(
        self,
        authorized_client: AsyncClient,
        test_link: dict,
    ):
        """Test adding tag not owned by current user."""
        # Create a tag with different owner
        from app.models.tag import Tag
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.db.session import async_session_maker

        async with async_session_maker() as session:
            other_user = User(
                email="tagowner@example.com",
                password_hash=get_password_hash("password"),
            )
            session.add(other_user)
            await session.commit()

            other_tag = Tag(
                name="other-tag",
                owner_id=other_user.id,
            )
            session.add(other_tag)
            await session.commit()
            other_tag_id = other_tag.id

        response = await authorized_client.post(
            f"/api/v1/links/{test_link.short}/tags/{other_tag_id}",
        )

        assert response.status_code == 404
