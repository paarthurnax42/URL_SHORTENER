from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


def create_rate_limiter() -> Limiter:
    """Создать и настроить rate limiter."""
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    )
    return limiter


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Обработчик превышения лимита."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests",
            "message": "Rate limit exceeded. Please try again later.",
        },
    )
