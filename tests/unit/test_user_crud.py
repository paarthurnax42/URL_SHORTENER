"""
Unit tests for user CRUD operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    authenticate_user,
)
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestCreateUser:
    """Tests for create_user function."""

    async def test_create_user_success(self, test_session: AsyncSession):
        """Test successful user creation."""
        user = await create_user(
            session=test_session,
            email="newuser@example.com",
            password="securepassword123",
        )

        assert user.email == "newuser@example.com"
        assert user.id is not None
        assert user.is_active is True
        assert "$" in user.password_hash

    async def test_create_user_duplicate_email(self, test_session: AsyncSession):
        """Test creating user with duplicate email raises error."""
        await create_user(
            session=test_session,
            email="duplicate@example.com",
            password="password123",
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_user(
                session=test_session,
                email="duplicate@example.com",
                password="anotherpassword",
            )

    async def test_create_user_password_hashed(self, test_session: AsyncSession):
        """Test that password is properly hashed."""
        user = await create_user(
            session=test_session,
            email="hashuser@example.com",
            password="testpassword",
        )

        # Password should be hashed, not stored in plain text
        assert user.password_hash != "testpassword"
        assert len(user.password_hash) > 50

    async def test_create_user_is_active_default(self, test_session: AsyncSession):
        """Test that new users are active by default."""
        user = await create_user(
            session=test_session,
            email="activeuser@example.com",
            password="password123",
        )

        assert user.is_active is True


@pytest.mark.asyncio
class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    async def test_get_user_by_email_exists(self, test_session: AsyncSession):
        """Test getting user that exists."""
        await create_user(
            session=test_session,
            email="findme@example.com",
            password="password123",
        )

        user = await get_user_by_email(test_session, "findme@example.com")

        assert user is not None
        assert user.email == "findme@example.com"

    async def test_get_user_by_email_not_exists(self, test_session: AsyncSession):
        """Test getting user that doesn't exist."""
        user = await get_user_by_email(test_session, "nonexistent@example.com")

        assert user is None

    async def test_get_user_by_email_case_sensitive(self, test_session: AsyncSession):
        """Test email lookup is case-sensitive."""
        await create_user(
            session=test_session,
            email="case@example.com",
            password="password123",
        )

        user = await get_user_by_email(test_session, "CASE@example.com")

        # SQLAlchemy default is case-sensitive for exact match
        assert user is None


@pytest.mark.asyncio
class TestGetUserById:
    """Tests for get_user_by_id function."""

    async def test_get_user_by_id_exists(self, test_session: AsyncSession):
        """Test getting user by ID that exists."""
        user = await create_user(
            session=test_session,
            email="byid@example.com",
            password="password123",
        )

        result = await get_user_by_id(test_session, user.id)

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    async def test_get_user_by_id_not_exists(self, test_session: AsyncSession):
        """Test getting user by ID that doesn't exist."""
        result = await get_user_by_id(test_session, 99999)

        assert result is None


@pytest.mark.asyncio
class TestAuthenticateUser:
    """Tests for authenticate_user function."""

    async def test_authenticate_success(self, test_session: AsyncSession):
        """Test successful authentication."""
        password = "correctpassword123"
        await create_user(
            session=test_session,
            email="auth@example.com",
            password=password,
        )

        user = await authenticate_user(
            session=test_session,
            email="auth@example.com",
            password=password,
        )

        assert user is not None
        assert user.email == "auth@example.com"

    async def test_authenticate_wrong_password(self, test_session: AsyncSession):
        """Test authentication with wrong password."""
        await create_user(
            session=test_session,
            email="wrongpass@example.com",
            password="correctpassword",
        )

        user = await authenticate_user(
            session=test_session,
            email="wrongpass@example.com",
            password="wrongpassword",
        )

        assert user is None

    async def test_authenticate_user_not_exists(self, test_session: AsyncSession):
        """Test authentication for non-existent user."""
        user = await authenticate_user(
            session=test_session,
            email="nonexistent@example.com",
            password="anypassword",
        )

        assert user is None

    async def test_authenticate_inactive_user(self, test_session: AsyncSession):
        """Test authentication for inactive user."""
        user = await create_user(
            session=test_session,
            email="inactive@example.com",
            password="password123",
        )

        # Deactivate user
        user.is_active = False
        await test_session.commit()

        result = await authenticate_user(
            session=test_session,
            email="inactive@example.com",
            password="password123",
        )

        assert result is None
