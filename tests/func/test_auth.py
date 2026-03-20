"""
Functional API tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register endpoint."""

    async def test_register_success(self, client: AsyncClient, sample_user_data: dict):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test registration with existing email returns 400."""
        duplicate_data = {
            "email": test_user.email,
            "password": "anotherpassword123",
        }

        response = await client.post("/api/v1/auth/register", json=duplicate_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        invalid_data = {
            "email": "not-an-email",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422  # Validation error

    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with password too short."""
        invalid_data = {
            "email": "shortpass@example.com",
            "password": "12345",  # Only 5 chars, minimum is 6
        }

        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422

    async def test_register_missing_email(self, client: AsyncClient):
        """Test registration without email."""
        invalid_data = {
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422

    async def test_register_missing_password(self, client: AsyncClient):
        """Test registration without password."""
        invalid_data = {
            "email": "nopass@example.com",
        }

        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint."""

    async def test_login_success(self, client: AsyncClient, test_user: dict):
        """Test successful login."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user: dict):
        """Test login with wrong password."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login for non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "anypassword",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format."""
        login_data = {
            "email": "invalid-email",
            "password": "password123",
        }

        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 422


@pytest.mark.asyncio
class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me endpoint."""

    async def test_get_me_authenticated(
        self,
        authorized_client: AsyncClient,
        test_user: dict,
    ):
        """Test getting current user info when authenticated."""
        response = await authorized_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert "is_active" in data
        assert "created_at" in data

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user info without authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Test getting current user info with invalid token."""
        client.headers["Authorization"] = "Bearer invalid-token-xyz"

        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_get_me_malformed_token(self, client: AsyncClient):
        """Test getting current user info with malformed token."""
        client.headers["Authorization"] = "Bearer not.a.valid.jwt.token"

        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthIntegration:
    """Integration tests for authentication flow."""

    async def test_register_then_login(self, client: AsyncClient):
        """Test registering then logging in."""
        register_data = {
            "email": "flow@example.com",
            "password": "flowpassword123",
        }

        # Register
        reg_response = await client.post("/api/v1/auth/register", json=register_data)
        assert reg_response.status_code == 201

        # Login with same credentials
        login_response = await client.post("/api/v1/auth/login", json=register_data)
        assert login_response.status_code == 200

    async def test_register_then_access_protected(
        self,
        client: AsyncClient,
    ):
        """Test registering then accessing protected endpoint."""
        register_data = {
            "email": "protected@example.com",
            "password": "protectedpass123",
        }

        # Register and get token
        reg_response = await client.post("/api/v1/auth/register", json=register_data)
        token = reg_response.json()["access_token"]

        # Access protected endpoint
        client.headers["Authorization"] = f"Bearer {token}"
        me_response = await client.get("/api/v1/auth/me")

        assert me_response.status_code == 200
        assert me_response.json()["email"] == register_data["email"]

    async def test_token_from_different_users(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test that tokens work for respective users."""
        # Create second user
        user2_data = {
            "email": "second@example.com",
            "password": "secondpassword123",
        }

        reg_response = await client.post("/api/v1/auth/register", json=user2_data)
        user2_token = reg_response.json()["access_token"]

        # Use user2's token
        client.headers["Authorization"] = f"Bearer {user2_token}"
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 200
        assert response.json()["email"] == user2_data["email"]
