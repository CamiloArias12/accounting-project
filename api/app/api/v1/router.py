"""Mounts each module's router. Adding a module is one import and one line."""

from fastapi import APIRouter

from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.locations.router import router as locations_router
from app.modules.third_parties.router import router as third_parties_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(locations_router)
api_router.include_router(third_parties_router)
