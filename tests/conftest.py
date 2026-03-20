"""
Test configuration and fixtures for URL shortener application.
Uses PostgreSQL in Docker for realistic testing.
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import AsyncGenerator, Generator
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load test environment variables from tests/.env
# This MUST happen before any app imports
load_dotenv(Path(__file__).parent / ".env", override=True)

# Clear any cached app modules to ensure they read fresh env vars
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('app'):
        del sys.modules[mod_name]

# Now import app modules - they will read from environment variables
from app.main import create_app
from app.db.base import Base
from app.models.links import Link
from app.models.user import User
from app.models.tag import Tag
from app.core.security import get_password_hash, create_access_token
from app.core.cache import link_cache


# Test database URL (PostgreSQL in Docker)
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_url_shortener"


def wait_for_postgres(timeout: int = 30) -> bool:
    """Wait for PostgreSQL to be ready."""
    import socket
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 5433))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    
    return False


def wait_for_redis(timeout: int = 10) -> bool:
    """Wait for Redis to be ready."""
    import socket
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 6380))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    
    return False


@pytest.fixture(scope="session", autouse=True)
def check_services():
    """Ensure test services are running before tests."""
    print("\n" + "="*60)
    print("Checking test services...")
    
    if not wait_for_postgres():
        pytest.fail("PostgreSQL is not available. Run: docker-compose -f docker-compose.test.yml up -d")
    
    if not wait_for_redis():
        print("Warning: Redis is not available. Cache tests will be skipped.")
    
    print("Test services are ready!")
    print("="*60 + "\n")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests (pytest-asyncio 0.23.x)."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine with fresh tables for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    # Drop and recreate all tables for each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncSession:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    from app.api.v1.dependencies import get_db_session
    from app.api.redirect import get_db_session_redirect

    async def get_db_session_override():
        yield test_session

    async def get_db_session_redirect_override():
        yield test_session

    app = create_app()
    app.dependency_overrides = {
        get_db_session: get_db_session_override,
        get_db_session_redirect: get_db_session_redirect_override,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac

    app.dependency_overrides = {}


@pytest_asyncio.fixture(scope="function")
async def test_user(test_session: AsyncSession) -> User:
    """Create test user."""
    import uuid
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("testpassword123"),
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_token(test_user: User) -> str:
    """Create JWT token for test user."""
    return create_access_token(subject=test_user.id)


@pytest_asyncio.fixture(scope="function")
async def authorized_client(
    client: AsyncClient,
    test_user_token: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Create authorized test HTTP client."""
    client.headers["Authorization"] = f"Bearer {test_user_token}"
    yield client
    client.headers.pop("Authorization")


@pytest_asyncio.fixture(scope="function")
async def test_link(test_session: AsyncSession, test_user: User) -> Link:
    """Create test link."""
    from app.crud.link import create_link
    import uuid
    
    link = await create_link(
        session=test_session,
        original=f"https://example.com/test-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
    )
    return link


@pytest_asyncio.fixture(scope="function")
async def test_link_with_alias(
    test_session: AsyncSession,
    test_user: User,
) -> Link:
    """Create test link with alias."""
    from app.crud.link import create_link
    import uuid
    
    link = await create_link(
        session=test_session,
        original=f"https://example.com/aliased-{uuid.uuid4().hex[:8]}",
        alias=f"my-alias-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
    )
    return link


@pytest_asyncio.fixture(scope="function")
async def test_expired_link(
    test_session: AsyncSession,
    test_user: User,
) -> Link:
    """Create expired test link."""
    from app.crud.link import create_link
    import uuid
    
    link = await create_link(
        session=test_session,
        original=f"https://example.com/expired-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
        expired_at=1,  # 1 minute
    )
    # Manually set as expired
    link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await test_session.commit()
    await test_session.refresh(link)
    return link


@pytest_asyncio.fixture(scope="function")
async def test_tag(test_session: AsyncSession, test_user: User) -> Tag:
    """Create test tag."""
    import uuid
    
    tag = Tag(
        name=f"test-tag-{uuid.uuid4().hex[:8]}",
        owner_id=test_user.id,
    )
    test_session.add(tag)
    await test_session.commit()
    await test_session.refresh(tag)
    return tag


@pytest.fixture
def sample_link_data() -> dict:
    """Sample link creation data."""
    return {
        "original": "https://example.com/very/long/url/path",
        "alias": "custom-alias",
        "expired_at": 60,
    }


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user registration data."""
    return {
        "email": "newuser@example.com",
        "password": "securepassword123",
    }


@pytest.fixture
def sample_tag_data() -> dict:
    """Sample tag creation data."""
    return {
        "name": "new-tag",
    }
