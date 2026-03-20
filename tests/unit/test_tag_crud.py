"""
Unit tests for tag CRUD operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.tag import (
    create_tag,
    get_tags,
    get_tag_by_id,
    delete_tag,
    add_tag_to_link,
    remove_tag_from_link,
    get_links_by_tag,
    search_links_by_tags,
)
from app.models.tag import Tag, link_tags
from app.models.links import Link
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestCreateTag:
    """Tests for create_tag function."""

    async def test_create_tag_success(self, test_session: AsyncSession):
        """Test successful tag creation."""
        tag = await create_tag(
            session=test_session,
            name="test-tag",
        )

        assert tag.name == "test-tag"
        assert tag.id is not None

    async def test_create_tag_with_owner(self, test_session: AsyncSession):
        """Test creating tag with owner ID."""
        user = User(
            email="tagowner@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()

        tag = await create_tag(
            session=test_session,
            name="owned-tag",
            owner_id=user.id,
        )

        assert tag.owner_id == user.id

    async def test_create_tag_duplicate_name(self, test_session: AsyncSession):
        """Test creating tag with duplicate name raises error."""
        await create_tag(
            session=test_session,
            name="duplicate-tag",
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_tag(
                session=test_session,
                name="duplicate-tag",
            )

    async def test_create_tag_case_insensitive(self, test_session: AsyncSession):
        """Test tag name uniqueness is case-insensitive."""
        await create_tag(
            session=test_session,
            name="case-tag",
        )

        with pytest.raises(ValueError, match="already exists"):
            await create_tag(
                session=test_session,
                name="CASE-TAG",
            )

    async def test_create_tag_duplicate_different_owner(
        self,
        test_session: AsyncSession,
    ):
        """Test same tag name allowed for different owners."""
        user1 = User(
            email="owner1@example.com",
            password_hash=get_password_hash("password"),
        )
        user2 = User(
            email="owner2@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add_all([user1, user2])
        await test_session.commit()

        tag1 = await create_tag(
            session=test_session,
            name="shared-name",
            owner_id=user1.id,
        )

        tag2 = await create_tag(
            session=test_session,
            name="shared-name",
            owner_id=user2.id,
        )

        assert tag1.id != tag2.id


@pytest.mark.asyncio
class TestGetTags:
    """Tests for get_tags function."""

    async def test_get_all_tags(self, test_session: AsyncSession):
        """Test getting all tags."""
        await create_tag(session=test_session, name="tag1")
        await create_tag(session=test_session, name="tag2")

        tags = await get_tags(test_session)

        assert len(tags) == 2

    async def test_get_tags_by_owner(self, test_session: AsyncSession):
        """Test getting tags filtered by owner."""
        user = User(
            email="tagfilter@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()

        await create_tag(session=test_session, name="user-tag", owner_id=user.id)
        await create_tag(session=test_session, name="public-tag")

        tags = await get_tags(test_session, owner_id=user.id)

        assert len(tags) == 1
        assert tags[0].name == "user-tag"

    async def test_get_tags_ordered_by_name(self, test_session: AsyncSession):
        """Test tags are ordered by name."""
        await create_tag(session=test_session, name="zebra")
        await create_tag(session=test_session, name="apple")
        await create_tag(session=test_session, name="mango")

        tags = await get_tags(test_session)

        assert tags[0].name == "apple"
        assert tags[1].name == "mango"
        assert tags[2].name == "zebra"


@pytest.mark.asyncio
class TestGetTagById:
    """Tests for get_tag_by_id function."""

    async def test_get_tag_by_id_exists(self, test_session: AsyncSession):
        """Test getting tag by existing ID."""
        tag = await create_tag(session=test_session, name="find-by-id")

        result = await get_tag_by_id(test_session, tag.id)

        assert result is not None
        assert result.id == tag.id

    async def test_get_tag_by_id_not_exists(self, test_session: AsyncSession):
        """Test getting tag by non-existent ID."""
        result = await get_tag_by_id(test_session, 99999)

        assert result is None

    async def test_get_tag_by_id_with_owner_filter(
        self,
        test_session: AsyncSession,
    ):
        """Test getting tag with owner filter."""
        user = User(
            email="ownerfilter@example.com",
            password_hash=get_password_hash("password"),
        )
        test_session.add(user)
        await test_session.commit()

        tag = await create_tag(
            session=test_session,
            name="owned-find",
            owner_id=user.id,
        )

        result = await get_tag_by_id(test_session, tag.id, owner_id=user.id)

        assert result is not None

        # Wrong owner should return None
        result_wrong = await get_tag_by_id(test_session, tag.id, owner_id=999)
        assert result_wrong is None


@pytest.mark.asyncio
class TestDeleteTag:
    """Tests for delete_tag function."""

    async def test_delete_tag_success(self, test_session: AsyncSession):
        """Test successful tag deletion."""
        tag = await create_tag(session=test_session, name="to-delete")

        await delete_tag(test_session, tag)

        # Verify deleted
        result = await get_tag_by_id(test_session, tag.id)
        assert result is None


@pytest.mark.asyncio
class TestAddTagToLink:
    """Tests for add_tag_to_link function."""

    async def test_add_tag_to_link(self, test_session: AsyncSession):
        """Test adding tag to link."""
        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="link-tag")

        await add_tag_to_link(test_session, link, tag)

        # Verify by querying the association table
        from sqlalchemy import select
        result = await test_session.execute(
            select(link_tags).where(
                link_tags.c.link_id == link.id,
                link_tags.c.tag_id == tag.id
            )
        )
        assert result.first() is not None

    async def test_add_tag_to_link_already_tagged(self, test_session: AsyncSession):
        """Test adding same tag twice doesn't duplicate."""
        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="single-tag")

        await add_tag_to_link(test_session, link, tag)
        await add_tag_to_link(test_session, link, tag)

        # Verify only one association exists
        from sqlalchemy import select, func
        result = await test_session.execute(
            select(func.count()).select_from(link_tags).where(
                link_tags.c.link_id == link.id,
                link_tags.c.tag_id == tag.id
            )
        )
        assert result.scalar() == 1


@pytest.mark.asyncio
class TestRemoveTagFromLink:
    """Tests for remove_tag_from_link function."""

    async def test_remove_tag_from_link(self, test_session: AsyncSession):
        """Test removing tag from link."""
        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="remove-tag")

        await add_tag_to_link(test_session, link, tag)
        await remove_tag_from_link(test_session, link, tag)

        # Verify association is removed
        from sqlalchemy import select
        result = await test_session.execute(
            select(link_tags).where(
                link_tags.c.link_id == link.id,
                link_tags.c.tag_id == tag.id
            )
        )
        assert result.first() is None

    async def test_remove_tag_not_attached(self, test_session: AsyncSession):
        """Test removing tag that's not attached doesn't error."""
        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="not-attached")

        await remove_tag_from_link(test_session, link, tag)  # Should not raise


@pytest.mark.asyncio
class TestGetLinksByTag:
    """Tests for get_links_by_tag function."""

    async def test_get_links_by_tag(self, test_session: AsyncSession):
        """Test getting links by tag."""
        link1 = await create_link_with_owner(test_session)
        link2 = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="multi-link-tag")

        await add_tag_to_link(test_session, link1, tag)
        await add_tag_to_link(test_session, link2, tag)

        links = await get_links_by_tag(test_session, tag)

        assert len(links) == 2
        assert link1.id in [l.id for l in links]
        assert link2.id in [l.id for l in links]

    async def test_get_links_by_tag_deleted_excluded(
        self,
        test_session: AsyncSession,
    ):
        """Test that deleted links are excluded."""
        from app.crud.link import delete_link

        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="deleted-link-tag")

        await add_tag_to_link(test_session, link, tag)
        await delete_link(test_session, link)

        links = await get_links_by_tag(test_session, tag)

        assert len(links) == 0


@pytest.mark.asyncio
class TestSearchLinksByTags:
    """Tests for search_links_by_tags function."""

    async def test_search_links_by_single_tag(self, test_session: AsyncSession):
        """Test searching links by single tag."""
        link = await create_link_with_owner(test_session)
        tag = await create_tag(session=test_session, name="search-tag")

        await add_tag_to_link(test_session, link, tag)

        links = await search_links_by_tags(test_session, ["search-tag"])

        assert len(links) == 1
        assert links[0].id == link.id

    async def test_search_links_by_multiple_tags_and_logic(
        self,
        test_session: AsyncSession,
    ):
        """Test searching links by multiple tags (AND logic)."""
        link1 = await create_link_with_owner(test_session)
        link2 = await create_link_with_owner(test_session)

        tag1 = await create_tag(session=test_session, name="and-tag-1")
        tag2 = await create_tag(session=test_session, name="and-tag-2")

        # link1 has both tags, link2 has only tag1
        await add_tag_to_link(test_session, link1, tag1)
        await add_tag_to_link(test_session, link1, tag2)
        await add_tag_to_link(test_session, link2, tag1)

        links = await search_links_by_tags(
            test_session,
            ["and-tag-1", "and-tag-2"],
        )

        assert len(links) == 1
        assert links[0].id == link1.id

    async def test_search_links_no_matching_tags(self, test_session: AsyncSession):
        """Test searching with non-existent tags."""
        links = await search_links_by_tags(
            test_session,
            ["nonexistent-tag-xyz"],
        )

        assert len(links) == 0


# Helper function
async def create_link_with_owner(session: AsyncSession) -> Link:
    """Create a link with an owner for testing."""
    from app.crud.link import create_link, encode_id
    import uuid
    
    unique_id = uuid.uuid4().hex[:8]
    
    user = User(
        email=f"linkowner-{unique_id}@example.com",
        password_hash=get_password_hash("password"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    link = await create_link(
        session=session,
        original=f"https://example.com/tagged-link-{unique_id}",
        owner_id=user.id,
    )
    # Refresh to get all attributes
    await session.refresh(link)
    return link
