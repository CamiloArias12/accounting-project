"""Aggregates the routers each module exposes.

Adding a module is one import and one `include_router` here; nothing else in
the codebase needs to know it exists.
"""

from fastapi import APIRouter

from app.modules.accounts.infrastructure.http.router import router as accounts_router
from app.modules.auth.infrastructure.http.router import router as auth_router
from app.modules.health.http.router import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
