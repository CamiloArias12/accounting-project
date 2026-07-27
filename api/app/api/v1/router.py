"""Mounts each module's router."""

from fastapi import APIRouter

from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router
from app.modules.exogena.router import router as exogena_router
from app.modules.health.router import router as health_router
from app.modules.ledger.router import router as ledger_router
from app.modules.locations.router import router as locations_router
from app.modules.periods.router import router as periods_router
from app.modules.third_parties.router import router as third_parties_router
from app.modules.uvt.router import router as uvt_router
from app.modules.vouchers.router import router as vouchers_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(locations_router)
api_router.include_router(third_parties_router)
api_router.include_router(periods_router)
api_router.include_router(vouchers_router)
api_router.include_router(ledger_router)
api_router.include_router(uvt_router)
api_router.include_router(exogena_router)
