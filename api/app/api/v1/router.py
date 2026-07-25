"""Mounts each module's router. Adding a module is one import and one line."""

from fastapi import APIRouter

from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
