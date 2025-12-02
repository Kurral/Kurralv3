"""
API v1 router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, api_keys, artifacts, stats


api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(stats.router, prefix="/stats", tags=["statistics"])

