"""Fills a freshly migrated database: a user to sign in with, and a chart of
accounts to work on.

Refuses to run outside `ENVIRONMENT=local`. A password written in a repository
is a development convenience, never a deployment step: real users are created
through `POST /auth/register`.

    docker compose -f docker-compose.local.yml exec api python -m app.seed
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from pathlib import Path

from sqlalchemy import select

from app.modules.accounts.models import Account
from app.modules.accounts.puc import Nature
from app.modules.auth.errors import EmailAlreadyRegistered
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.service import AuthService
from app.shared.config import settings
from app.shared.database import SessionFactory

DEFAULT_EMAIL = "admin@local.dev"
DEFAULT_PASSWORD = "local-admin-2026"
DEFAULT_FULL_NAME = "Admin Local"

#: The same plan as `fixtures/puc.xlsx`, with the two columns the spreadsheet
#: format has no room for: the DIAN concept an account reports under, and
#: whether it holds a withholding.
PUC_FILE = Path(__file__).resolve().parents[1] / "fixtures" / "puc.csv"


async def seed_user() -> int:
    if settings.ENVIRONMENT != "local":
        print(
            f"seed: refusing to run with ENVIRONMENT={settings.ENVIRONMENT}",
            file=sys.stderr,
        )
        return 1

    payload = RegisterRequest(
        email=os.environ.get("SEED_EMAIL", DEFAULT_EMAIL),
        password=os.environ.get("SEED_PASSWORD", DEFAULT_PASSWORD),
        full_name=os.environ.get("SEED_FULL_NAME", DEFAULT_FULL_NAME),
    )

    async with SessionFactory() as session:
        try:
            # Through the service, so the password is hashed by the same code
            # that hashes it on registration.
            await AuthService(session).register(payload)
        except EmailAlreadyRegistered:
            # Running it twice is the normal case, not a failure.
            print(f"seed: {payload.email} already exists")
            return 0

    print(f"seed: created {payload.email} / {payload.password}")
    return 0


async def seed_accounts() -> None:
    async with SessionFactory() as session:
        existing = set((await session.execute(select(Account.code))).scalars().all())

        created = 0
        # Shortest code first: a child cannot be inserted before the parent its
        # prefix points at.
        for row in sorted(_puc_rows(), key=lambda r: len(r["code"])):
            if row["code"] in existing:
                continue

            session.add(
                Account.open(
                    code=row["code"],
                    name=row["name"],
                    nature=Nature(row["nature"]),
                    requires_third_party=row["requires_third_party"] == "true",
                    is_withholding=row["is_withholding"] == "true",
                    dian_concept=row["dian_concept"] or None,
                )
            )
            created += 1

        await session.commit()

    kept = len(existing)
    print(f"seed: {created} accounts created, {kept} already there")


def _puc_rows() -> list[dict[str, str]]:
    with PUC_FILE.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


async def main() -> int:
    code = await seed_user()
    if code == 0:
        await seed_accounts()
    return code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
