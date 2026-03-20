from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from app.db.session import async_session_maker
from app.crud.link import cleanup_old_links, get_expired_links


async def cleanup_expired_links():
    """Удалить просроченные ссылки."""
    async with async_session_maker() as session:
        links = await get_expired_links(session, limit=100)
        for link in links:
            link.deleted_at = datetime.now(timezone.utc)
        await session.commit()
        return len(links)


async def cleanup_unused_links_job():
    """Удалить неиспользуемые ссылки."""
    async with async_session_maker() as session:
        from app.core.config import settings
        count = await cleanup_old_links(session, days=settings.UNUSED_LINKS_DAYS)
        return count


def create_scheduler() -> AsyncIOScheduler:
    """Создать и настроить планировщик."""
    scheduler = AsyncIOScheduler()
    
    # Очистка просроченных ссылок - каждый час
    scheduler.add_job(
        cleanup_expired_links,
        trigger=CronTrigger(minute=0),  # Каждый час в 0 минут
        id='cleanup_expired',
        name='Cleanup expired links',
        replace_existing=True,
    )
    
    # Очистка неиспользуемых ссылок - раз в день в 3:00
    scheduler.add_job(
        cleanup_unused_links_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='cleanup_unused',
        name='Cleanup unused links',
        replace_existing=True,
    )
    
    return scheduler


# Глобальный планировщик
scheduler = create_scheduler()
