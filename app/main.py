from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.api.redirect import router as redirect_router
from app.core.config import settings
from app.core.rate_limiter import create_rate_limiter, rate_limit_handler
from app.core.cache import link_cache
from app.core.scheduler import scheduler


def create_app() -> FastAPI:
    app = FastAPI()

    # CORS для фронтенда
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    limiter = create_rate_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    # API роуты (/api/v1/*)
    app.include_router(api_router, prefix="/api/v1")

    # Редирект ссылок (на корневом уровне: /links/{code})
    app.include_router(redirect_router)

    # Подключение к Redis при старте
    @app.on_event("startup")
    async def startup():
        await link_cache.connect()
        scheduler.start()

    # Отключение от Redis при остановке
    @app.on_event("shutdown")
    async def shutdown():
        await link_cache.disconnect()
        scheduler.shutdown()

    return app


app = create_app()
