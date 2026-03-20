"""
Test fixtures for URL shortener application.
Provides pre-seeded data for testing.
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.links import Link
from app.models.tag import Tag
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="class")
def test_user_data():
    """Test user credentials."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
    }


@pytest.fixture(scope="class")
def admin_user_data():
    """Admin user credentials."""
    return {
        "email": "admin@example.com",
        "password": "adminpassword123",
    }


@pytest.fixture(scope="class")
def sample_links_data():
    """Sample links for testing."""
    return [
        {
            "original": "https://example.com/page1",
            "alias": "page1",
            "clicks_count": 10,
        },
        {
            "original": "https://example.com/page2",
            "alias": "page2",
            "clicks_count": 5,
        },
        {
            "original": "https://google.com/search",
            "alias": None,
            "clicks_count": 0,
        },
        {
            "original": "https://github.com/repo",
            "alias": "github",
            "clicks_count": 25,
        },
    ]


@pytest.fixture(scope="class")
def sample_tags_data():
    """Sample tags for testing."""
    return [
        {"name": "social-media"},
        {"name": "work"},
        {"name": "personal"},
        {"name": "important"},
    ]


@pytest.fixture(scope="class")
def expired_links_data():
    """Expired links for testing."""
    return [
        {
            "original": "https://example.com/expired1",
            "expired_minutes": -60,  # Expired 1 hour ago
        },
        {
            "original": "https://example.com/expired2",
            "expired_minutes": -1440,  # Expired 1 day ago
        },
    ]


@pytest.fixture(scope="class")
def test_user(test_session, test_user_data) -> User:
    """Create test user."""
    user = User(
        email=test_user_data["email"],
        password_hash=get_password_hash(test_user_data["password"]),
        is_active=True,
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="class")
def admin_user(test_session, admin_user_data) -> User:
    """Create admin user."""
    user = User(
        email=admin_user_data["email"],
        password_hash=get_password_hash(admin_user_data["password"]),
        is_active=True,
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="class")
def test_user_token(test_user) -> str:
    """Create JWT token for test user."""
    return create_access_token(subject=test_user.id)


@pytest.fixture(scope="class")
def admin_user_token(admin_user) -> str:
    """Create JWT token for admin user."""
    return create_access_token(subject=admin_user.id)


@pytest.fixture(scope="class")
def user_links(test_session, test_user, sample_links_data) -> list[Link]:
    """Create sample links for test user."""
    from app.crud.link import create_link
    
    links = []
    for link_data in sample_links_data:
        link = Link(
            original=link_data["original"],
            alias=link_data["alias"],
            short="",  # Will be generated
            owner_id=test_user.id,
            clicks_count=link_data["clicks_count"],
        )
        test_session.add(link)
        test_session.flush()  # Generate ID
        
        # Generate short code using sqids
        from app.crud.link import encode_id
        link.short = encode_id(link.id)
        links.append(link)
    
    test_session.commit()
    
    # Refresh to get short codes
    for link in links:
        test_session.refresh(link)
    
    return links


@pytest.fixture(scope="class")
def user_tags(test_session, test_user, sample_tags_data) -> list[Tag]:
    """Create sample tags for test user."""
    tags = []
    for tag_data in sample_tags_data:
        tag = Tag(
            name=tag_data["name"],
            owner_id=test_user.id,
        )
        test_session.add(tag)
        tags.append(tag)
    
    test_session.commit()
    
    for tag in tags:
        test_session.refresh(tag)
    
    return tags


@pytest.fixture(scope="class")
def expired_links(test_session, test_user, expired_links_data) -> list[Link]:
    """Create expired links for testing."""
    from app.crud.link import create_link
    
    links = []
    for link_data in expired_links_data:
        link = Link(
            original=link_data["original"],
            owner_id=test_user.id,
            expired_at=datetime.now(timezone.utc) + timedelta(minutes=link_data["expired_minutes"]),
        )
        test_session.add(link)
        test_session.flush()
        
        from app.crud.link import encode_id
        link.short = encode_id(link.id)
        links.append(link)
    
    test_session.commit()
    
    for link in links:
        test_session.refresh(link)
    
    return links


@pytest.fixture(scope="class")
def tagged_links(test_session, test_user, user_tags):
    """Create links with tags attached."""
    from app.crud.link import create_link
    from app.crud.tag import add_tag_to_link
    from sqlalchemy import select
    
    links = []
    
    # Link with multiple tags
    link1 = Link(
        original="https://example.com/tagged-multi",
        owner_id=test_user.id,
    )
    test_session.add(link1)
    test_session.flush()
    link1.short = encode_id(link1.id)
    links.append(link1)
    
    # Link with single tag
    link2 = Link(
        original="https://example.com/tagged-single",
        owner_id=test_user.id,
    )
    test_session.add(link2)
    test_session.flush()
    link2.short = encode_id(link2.id)
    links.append(link2)
    
    test_session.commit()
    
    # Add tags to links
    if len(user_tags) >= 2:
        # link1 gets first two tags
        test_session.execute(
            select(Link).where(Link.id == link1.id)
        )
        test_session.execute(
            select(Tag).where(Tag.id == user_tags[0].id)
        )
        
        from app.models.tag import link_tags as link_tags_table
        test_session.execute(
            link_tags_table.insert().values(link_id=link1.id, tag_id=user_tags[0].id)
        )
        test_session.execute(
            link_tags_table.insert().values(link_id=link1.id, tag_id=user_tags[1].id)
        )
        
        # link2 gets first tag only
        test_session.execute(
            link_tags_table.insert().values(link_id=link2.id, tag_id=user_tags[0].id)
        )
        
        test_session.commit()
    
    return links


@pytest.fixture(scope="class")
def fill_tables(
    test_user,
    admin_user,
    user_links,
    user_tags,
    expired_links,
    tagged_links,
):
    """
    Fill all test tables with sample data.
    Use this fixture when you need pre-populated database.
    """
    # All data is already created by dependent fixtures
    yield
    
    # Cleanup happens automatically via test_session fixture


# Helper function for encoding
def encode_id(id: int) -> str:
    from sqids import Sqids
    sqids = Sqids(min_length=6)
    return sqids.encode([id])
