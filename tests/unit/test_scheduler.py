"""
Tests for scheduler with proper mocking.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.scheduler import (
    cleanup_expired_links,
    cleanup_unused_links_job,
    create_scheduler,
)
from app.crud.link import create_link


@pytest.mark.asyncio
class TestCleanupExpiredLinks:
    """Tests for cleanup_expired_links function."""

    async def test_cleanup_expired_links_success(self, test_session, test_user):
        """Test cleaning up expired links."""
        # Create expired link using create_link
        link = await create_link(
            session=test_session,
            original="https://example.com/expired-cleanup",
            owner_id=test_user.id,
            expired_at=1,
        )
        
        # Manually expire
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()
        
        # Mock async_session_maker properly for async context manager
        async def async_context_manager():
            yield test_session
        
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_expired_links()
        
        # Verify link was marked as deleted
        assert count >= 1
        await test_session.refresh(link)
        assert link.deleted_at is not None

    async def test_cleanup_expired_links_no_expired(self, test_session, test_user):
        """Test cleanup when no expired links exist."""
        # Create active link
        link = await create_link(
            session=test_session,
            original="https://example.com/active-cleanup",
            owner_id=test_user.id,
            expired_at=60,  # 60 minutes in future
        )
        
        # Mock async_session_maker
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_expired_links()
        
        # No links should be cleaned
        assert count == 0


@pytest.mark.asyncio
class TestCleanupUnusedLinksJob:
    """Tests for cleanup_unused_links_job function."""

    async def test_cleanup_unused_links_success(self, test_session, test_user):
        """Test cleaning up unused links."""
        import uuid
        
        # Create old unused link using create_link
        link = await create_link(
            session=test_session,
            original=f"https://example.com/old-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        
        # Manually set as old and unused
        link.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        link.last_used_at = None
        await test_session.commit()
        
        # Mock async_session_maker
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_unused_links_job()
        
        # Verify link was marked as deleted
        assert count >= 1
        await test_session.refresh(link)
        assert link.deleted_at is not None

    async def test_cleanup_unused_links_recent_link(self, test_session, test_user):
        """Test that recent links are not cleaned."""
        import uuid
        
        # Create recent link with recent activity
        link = await create_link(
            session=test_session,
            original=f"https://example.com/recent-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
        )
        
        # Set as recently used
        link.created_at = datetime.now(timezone.utc) - timedelta(days=5)
        link.last_used_at = datetime.now(timezone.utc) - timedelta(days=2)
        await test_session.commit()
        
        # Mock async_session_maker
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_unused_links_job()
        
        # Recent link should not be cleaned
        assert count == 0
        await test_session.refresh(link)
        assert link.deleted_at is None


class TestCreateScheduler:
    """Tests for create_scheduler function."""

    def test_create_scheduler_returns_scheduler(self):
        """Test that create_scheduler returns a scheduler."""
        scheduler = create_scheduler()
        
        assert scheduler is not None
        assert hasattr(scheduler, "add_job")
        assert hasattr(scheduler, "get_jobs")

    def test_create_scheduler_has_cleanup_jobs(self):
        """Test that scheduler has cleanup jobs."""
        scheduler = create_scheduler()
        
        jobs = scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        
        assert "cleanup_expired" in job_ids
        assert "cleanup_unused" in job_ids

    def test_create_scheduler_job_count(self):
        """Test that scheduler has exactly 2 jobs."""
        scheduler = create_scheduler()
        
        jobs = scheduler.get_jobs()
        assert len(jobs) == 2

    def test_create_scheduler_job_triggers(self):
        """Test that scheduler jobs have cron triggers."""
        scheduler = create_scheduler()
        
        jobs = scheduler.get_jobs()
        
        for job in jobs:
            # Verify trigger type
            trigger_type = type(job.trigger).__name__
            assert "cron" in trigger_type.lower()

    def test_create_scheduler_job_names(self):
        """Test that scheduler jobs have descriptive names."""
        scheduler = create_scheduler()
        
        jobs = scheduler.get_jobs()
        
        for job in jobs:
            assert job.name is not None
            assert len(job.name) > 0

    def test_create_scheduler_replace_existing(self):
        """Test that scheduler replaces existing jobs."""
        # Create scheduler twice
        scheduler1 = create_scheduler()
        scheduler2 = create_scheduler()
        
        # Should still have 2 jobs (not 4)
        assert len(scheduler2.get_jobs()) == 2


@pytest.mark.asyncio
class TestSchedulerIntegration:
    """Integration tests for scheduler."""

    async def test_cleanup_respects_deleted_at(self, test_session, test_user):
        """Test that cleanup doesn't re-delete already deleted links."""
        import uuid
        
        # Create already deleted link
        link = await create_link(
            session=test_session,
            original=f"https://example.com/deleted-{uuid.uuid4().hex[:8]}",
            owner_id=test_user.id,
            expired_at=1,
        )
        
        link.expired_at = datetime.now(timezone.utc) - timedelta(hours=2)
        link.deleted_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()
        
        # Mock async_session_maker
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_expired_links()
        
        # Already deleted link should not be counted
        assert count == 0

    async def test_cleanup_handles_multiple_links(self, test_session, test_user):
        """Test cleanup handles multiple expired links."""
        import uuid
        
        # Create multiple expired links
        links = []
        for i in range(5):
            link = await create_link(
                session=test_session,
                original=f"https://example.com/expired-{i}-{uuid.uuid4().hex[:8]}",
                owner_id=test_user.id,
                expired_at=1,
            )
            link.expired_at = datetime.now(timezone.utc) - timedelta(hours=i+1)
            links.append(link)
        await test_session.commit()
        
        # Mock async_session_maker
        mock_maker = MagicMock()
        mock_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
        mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.core.scheduler.async_session_maker", mock_maker):
            count = await cleanup_expired_links()
        
        # All expired links should be marked as deleted
        assert count >= 5
        for link in links:
            await test_session.refresh(link)
            assert link.deleted_at is not None
