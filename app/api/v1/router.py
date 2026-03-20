from fastapi import APIRouter

from app.api.v1 import link_shortener
from app.api.v1 import auth
from app.api.v1 import tags


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(link_shortener.router)
api_router.include_router(tags.router)

__all__ = ["api_router"]
